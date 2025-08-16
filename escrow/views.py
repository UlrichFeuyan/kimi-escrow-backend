from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Avg
import logging

from .models import EscrowTransaction, Milestone, Proof, TransactionMessage, TransactionRating
from .serializers import (
    EscrowTransactionListSerializer, EscrowTransactionDetailSerializer,
    EscrowTransactionCreateSerializer, TransactionActionSerializer,
    MilestoneSerializer, MilestoneActionSerializer, ProofSerializer,
    TransactionMessageSerializer, TransactionRatingSerializer
)
from core.permissions import (
    CanCreateEscrow, IsTransactionParticipant, IsKYCVerified,
    IsTransactionInCorrectState
)
from core.utils import APIResponseMixin
from .tasks import (
    send_transaction_notification, process_escrow_payment,
    auto_release_funds, send_milestone_notification
)

User = get_user_model()
logger = logging.getLogger(__name__)


class EscrowTransactionListCreateView(generics.ListCreateAPIView, APIResponseMixin):
    """Liste et création des transactions escrow"""
    permission_classes = [permissions.IsAuthenticated, IsKYCVerified]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EscrowTransactionCreateSerializer
        return EscrowTransactionListSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = EscrowTransaction.objects.filter(
            Q(buyer=user) | Q(seller=user)
        ).select_related('buyer', 'seller')
        
        # Filtres
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        category_filter = self.request.query_params.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        role_filter = self.request.query_params.get('role')
        if role_filter == 'buyer':
            queryset = queryset.filter(buyer=user)
        elif role_filter == 'seller':
            queryset = queryset.filter(seller=user)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        if not self.request.user.can_create_escrow():
            raise permissions.PermissionDenied("Vous ne pouvez pas créer de transactions escrow.")
        
        transaction_obj = serializer.save()
        
        send_transaction_notification.delay(
            transaction_obj.id,
            'created',
            f"Nouvelle transaction escrow créée: {transaction_obj.title}"
        )
        
        return transaction_obj


class EscrowTransactionDetailView(generics.RetrieveUpdateAPIView, APIResponseMixin):
    """Détail d'une transaction escrow"""
    serializer_class = EscrowTransactionDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_queryset(self):
        return EscrowTransaction.objects.select_related('buyer', 'seller').prefetch_related(
            'milestones', 'proofs', 'messages', 'ratings'
        )
    
    def get_object(self):
        transaction_obj = super().get_object()
        
        # Marquer les messages comme lus pour l'utilisateur actuel
        TransactionMessage.objects.filter(
            transaction=transaction_obj,
            is_read=False
        ).exclude(sender=self.request.user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return transaction_obj


class TransactionActionView(APIView, APIResponseMixin):
    """Actions sur les transactions"""
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_transaction(self):
        try:
            return EscrowTransaction.objects.get(
                id=self.kwargs['pk'],
                **{Q(buyer=self.request.user) | Q(seller=self.request.user): True}
            )
        except EscrowTransaction.DoesNotExist:
            return None
    
    def post(self, request, pk):
        transaction_obj = self.get_transaction()
        if not transaction_obj:
            return self.error_response("Transaction non trouvée", status_code=404)
        
        serializer = TransactionActionSerializer(
            data=request.data,
            context={'transaction': transaction_obj, 'request': request}
        )
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            
            try:
                with transaction.atomic():
                    if action == 'cancel':
                        result = self._cancel_transaction(transaction_obj, notes)
                    elif action == 'mark_delivered':
                        result = self._mark_delivered(transaction_obj, notes)
                    elif action == 'confirm_delivery':
                        result = self._confirm_delivery(transaction_obj, notes)
                    elif action == 'request_release':
                        result = self._request_release(transaction_obj, notes)
                    else:
                        return self.error_response("Action non supportée")
                    
                    return self.success_response(result)
                    
            except Exception as e:
                logger.error(f"Erreur action transaction {pk}: {e}")
                return self.error_response(
                    "Erreur lors de l'exécution de l'action",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return self.error_response("Données invalides", errors=serializer.errors)
    
    def _cancel_transaction(self, transaction_obj, notes):
        transaction_obj.status = 'CANCELLED'
        transaction_obj.cancelled_at = timezone.now()
        transaction_obj.notes = f"{transaction_obj.notes}\nAnnulé: {notes}".strip()
        transaction_obj.save()
        
        send_transaction_notification.delay(
            transaction_obj.id,
            'cancelled',
            f"Transaction annulée: {notes}"
        )
        
        return {
            'message': 'Transaction annulée avec succès',
            'transaction': EscrowTransactionDetailSerializer(transaction_obj).data
        }
    
    def _mark_delivered(self, transaction_obj, notes):
        transaction_obj.status = 'DELIVERED'
        transaction_obj.delivered_at = timezone.now()
        transaction_obj.notes = f"{transaction_obj.notes}\nLivré: {notes}".strip()
        
        if transaction_obj.auto_release_enabled:
            transaction_obj.auto_release_date = timezone.now() + timezone.timedelta(
                days=transaction_obj.auto_release_days
            )
        
        transaction_obj.save()
        
        if transaction_obj.auto_release_date:
            auto_release_funds.apply_async(
                args=[transaction_obj.id],
                eta=transaction_obj.auto_release_date
            )
        
        send_transaction_notification.delay(
            transaction_obj.id,
            'delivered',
            f"Transaction marquée comme livrée: {notes}"
        )
        
        return {
            'message': 'Transaction marquée comme livrée',
            'transaction': EscrowTransactionDetailSerializer(transaction_obj).data
        }
    
    def _confirm_delivery(self, transaction_obj, notes):
        transaction_obj.status = 'RELEASED'
        transaction_obj.released_at = timezone.now()
        transaction_obj.notes = f"{transaction_obj.notes}\nLivraison confirmée: {notes}".strip()
        transaction_obj.save()
        
        process_escrow_payment.delay(transaction_obj.id, 'release')
        
        send_transaction_notification.delay(
            transaction_obj.id,
            'released',
            f"Livraison confirmée, fonds libérés: {notes}"
        )
        
        return {
            'message': 'Livraison confirmée, fonds en cours de libération',
            'transaction': EscrowTransactionDetailSerializer(transaction_obj).data
        }
    
    def _request_release(self, transaction_obj, notes):
        TransactionMessage.objects.create(
            transaction=transaction_obj,
            sender=self.request.user,
            message=f"Demande de libération anticipée des fonds: {notes}",
            is_system_message=True
        )
        
        other_participant = transaction_obj.get_other_participant(self.request.user)
        send_transaction_notification.delay(
            transaction_obj.id,
            'release_requested',
            f"Demande de libération anticipée des fonds",
            user_id=other_participant.id
        )
        
        return {
            'message': 'Demande de libération envoyée',
            'transaction': EscrowTransactionDetailSerializer(transaction_obj).data
        }


class TransactionMessageListCreateView(generics.ListCreateAPIView, APIResponseMixin):
    """Messages d'une transaction"""
    serializer_class = TransactionMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_queryset(self):
        transaction_id = self.kwargs['transaction_id']
        return TransactionMessage.objects.filter(
            transaction_id=transaction_id
        ).select_related('sender').order_by('created_at')
    
    def perform_create(self, serializer):
        transaction_id = self.kwargs['transaction_id']
        transaction_obj = EscrowTransaction.objects.get(id=transaction_id)
        
        if self.request.user not in [transaction_obj.buyer, transaction_obj.seller]:
            raise permissions.PermissionDenied("Vous n'êtes pas participant à cette transaction.")
        
        serializer.save(
            transaction=transaction_obj,
            sender=self.request.user
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def transaction_statistics(request):
    """Statistiques des transactions de l'utilisateur"""
    user = request.user
    
    total_purchases = EscrowTransaction.objects.filter(buyer=user).count()
    total_sales = EscrowTransaction.objects.filter(seller=user).count()
    
    successful_purchases = EscrowTransaction.objects.filter(buyer=user, status='RELEASED').count()
    successful_sales = EscrowTransaction.objects.filter(seller=user, status='RELEASED').count()
    
    purchase_volume = EscrowTransaction.objects.filter(
        buyer=user, status='RELEASED'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    sales_volume = EscrowTransaction.objects.filter(
        seller=user, status='RELEASED'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    avg_rating = TransactionRating.objects.filter(
        rated_user=user
    ).aggregate(Avg('rating'))['rating__avg']
    
    rating_count = TransactionRating.objects.filter(rated_user=user).count()
    
    stats = {
        'purchases': {
            'total': total_purchases,
            'successful': successful_purchases,
            'success_rate': (successful_purchases / total_purchases * 100) if total_purchases > 0 else 0,
            'total_volume': float(purchase_volume),
        },
        'sales': {
            'total': total_sales,
            'successful': successful_sales,
            'success_rate': (successful_sales / total_sales * 100) if total_sales > 0 else 0,
            'total_volume': float(sales_volume),
        },
        'rating': {
            'average': float(avg_rating) if avg_rating else 0,
            'count': rating_count,
        },
        'total_transactions': total_purchases + total_sales,
        'total_volume': float(purchase_volume + sales_volume),
    }
    
    return Response({
        'success': True,
        'data': stats,
        'timestamp': timezone.now().isoformat()
    })


class FaceToFaceMeetingView(APIView, APIResponseMixin):
    """Gestion des rencontres face-à-face"""
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_transaction(self):
        try:
            return EscrowTransaction.objects.get(
                id=self.kwargs['pk'],
                transaction_type='FACE_TO_FACE',
                **{Q(buyer=self.request.user) | Q(seller=self.request.user): True}
            )
        except EscrowTransaction.DoesNotExist:
            return None
    
    def post(self, request, pk):
        """Actions sur une rencontre face-à-face"""
        transaction_obj = self.get_transaction()
        if not transaction_obj:
            return self.error_response("Transaction face-à-face non trouvée", status_code=404)
        
        action = request.data.get('action')
        
        if action == 'start_meeting':
            return self._start_meeting(transaction_obj, request)
        elif action == 'complete_meeting':
            return self._complete_meeting(transaction_obj, request)
        elif action == 'submit_proof':
            return self._submit_proof(transaction_obj, request)
        else:
            return self.error_response("Action non supportée")
    
    def _start_meeting(self, transaction_obj, request):
        """Démarrer une rencontre"""
        try:
            face_to_face = transaction_obj.face_to_face_details
            face_to_face.meeting_status = 'IN_PROGRESS'
            face_to_face.save()
            
            # Créer un message système
            TransactionMessage.objects.create(
                transaction=transaction_obj,
                sender=request.user,
                message="Rencontre face-à-face démarrée",
                is_system_message=True
            )
            
            return self.success_response({
                'message': 'Rencontre démarrée',
                'meeting_status': face_to_face.meeting_status
            })
        except Exception as e:
            logger.error(f"Erreur démarrage rencontre: {e}")
            return self.error_response("Erreur lors du démarrage de la rencontre")
    
    def _complete_meeting(self, transaction_obj, request):
        """Terminer une rencontre"""
        try:
            face_to_face = transaction_obj.face_to_face_details
            face_to_face.meeting_status = 'COMPLETED'
            face_to_face.save()
            
            # Marquer comme livré
            transaction_obj.status = 'DELIVERED'
            transaction_obj.delivered_at = timezone.now()
            transaction_obj.save()
            
            # Créer un message système
            TransactionMessage.objects.create(
                transaction=transaction_obj,
                sender=request.user,
                message="Rencontre face-à-face terminée - Transaction livrée",
                is_system_message=True
            )
            
            return self.success_response({
                'message': 'Rencontre terminée et transaction livrée',
                'transaction_status': transaction_obj.status
            })
        except Exception as e:
            logger.error(f"Erreur fin rencontre: {e}")
            return self.error_response("Erreur lors de la finalisation de la rencontre")
    
    def _submit_proof(self, transaction_obj, request):
        """Soumettre une preuve de rencontre"""
        try:
            proof_type = request.data.get('proof_type')
            title = request.data.get('title')
            description = request.data.get('description', '')
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            location_address = request.data.get('location_address', '')
            
            proof = Proof.objects.create(
                transaction=transaction_obj,
                proof_type=proof_type,
                title=title,
                description=description,
                latitude=latitude,
                longitude=longitude,
                location_address=location_address,
                submitted_by=request.user
            )
            
            # Mettre à jour les détails face-à-face
            face_to_face = transaction_obj.face_to_face_details
            if proof_type == 'FACE_TO_FACE_INITIAL':
                face_to_face.initial_proof = proof
            elif proof_type == 'FACE_TO_FACE_FINAL':
                face_to_face.final_proof = proof
            face_to_face.save()
            
            return self.success_response({
                'message': 'Preuve soumise avec succès',
                'proof_id': proof.id
            })
        except Exception as e:
            logger.error(f"Erreur soumission preuve: {e}")
            return self.error_response("Erreur lors de la soumission de la preuve")


class MilestoneManagementView(APIView, APIResponseMixin):
    """Gestion des jalons"""
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_milestone(self):
        try:
            return Milestone.objects.get(
                id=self.kwargs['milestone_id'],
                transaction__id=self.kwargs['pk'],
                **{Q(transaction__buyer=self.request.user) | Q(transaction__seller=self.request.user): True}
            )
        except Milestone.DoesNotExist:
            return None
    
    def post(self, request, pk, milestone_id):
        """Actions sur un jalon"""
        milestone = self.get_milestone()
        if not milestone:
            return self.error_response("Jalon non trouvé", status_code=404)
        
        serializer = MilestoneActionSerializer(
            data=request.data,
            context={'milestone': milestone, 'request': request}
        )
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            
            try:
                with transaction.atomic():
                    if action == 'complete':
                        result = self._complete_milestone(milestone, notes)
                    elif action == 'approve':
                        result = self._approve_milestone(milestone, notes)
                    elif action == 'reject':
                        result = self._reject_milestone(milestone, notes)
                    else:
                        return self.error_response("Action non supportée")
                    
                    return self.success_response(result)
                    
            except Exception as e:
                logger.error(f"Erreur action jalon {milestone_id}: {e}")
                return self.error_response(
                    "Erreur lors de l'exécution de l'action",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return self.error_response("Données invalides", errors=serializer.errors)
    
    def _complete_milestone(self, milestone, notes):
        """Marquer un jalon comme terminé"""
        milestone.status = 'COMPLETED'
        milestone.completed_at = timezone.now()
        milestone.completed_by = self.request.user
        milestone.completion_notes = notes
        milestone.save()
        
        send_milestone_notification.delay(
            milestone.id,
            'completed',
            f"Jalon terminé: {notes}"
        )
        
        return {
            'message': 'Jalon marqué comme terminé',
            'milestone': MilestoneSerializer(milestone).data
        }
    
    def _approve_milestone(self, milestone, notes):
        """Approuver un jalon"""
        milestone.status = 'APPROVED'
        milestone.approved_at = timezone.now()
        milestone.approved_by = self.request.user
        milestone.approval_notes = notes
        milestone.save()
        
        # Libérer les fonds du jalon
        # TODO: Implémenter la logique de libération des fonds
        
        send_milestone_notification.delay(
            milestone.id,
            'approved',
            f"Jalon approuvé: {notes}"
        )
        
        return {
            'message': 'Jalon approuvé',
            'milestone': MilestoneSerializer(milestone).data
        }
    
    def _reject_milestone(self, milestone, notes):
        """Rejeter un jalon"""
        milestone.status = 'REJECTED'
        milestone.approval_notes = notes
        milestone.save()
        
        send_milestone_notification.delay(
            milestone.id,
            'rejected',
            f"Jalon rejeté: {notes}"
        )
        
        return {
            'message': 'Jalon rejeté',
            'milestone': MilestoneSerializer(milestone).data
        }


class InternationalTransactionView(APIView, APIResponseMixin):
    """Gestion des transactions internationales"""
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_transaction(self):
        try:
            return EscrowTransaction.objects.get(
                id=self.kwargs['pk'],
                transaction_type='INTERNATIONAL',
                **{Q(buyer=self.request.user) | Q(seller=self.request.user): True}
            )
        except EscrowTransaction.DoesNotExist:
            return None
    
    def post(self, request, pk):
        """Actions sur une transaction internationale"""
        transaction_obj = self.get_transaction()
        if not transaction_obj:
            return self.error_response("Transaction internationale non trouvée", status_code=404)
        
        action = request.data.get('action')
        
        if action == 'update_tracking':
            return self._update_tracking(transaction_obj, request)
        elif action == 'submit_documents':
            return self._submit_documents(transaction_obj, request)
        elif action == 'extend_inspection':
            return self._extend_inspection(transaction_obj, request)
        else:
            return self.error_response("Action non supportée")
    
    def _update_tracking(self, transaction_obj, request):
        """Mettre à jour les informations de suivi"""
        try:
            international = transaction_obj.international_details
            international.tracking_number = request.data.get('tracking_number', international.tracking_number)
            international.tracking_url = request.data.get('tracking_url', international.tracking_url)
            international.save()
            
            return self.success_response({
                'message': 'Informations de suivi mises à jour',
                'tracking_number': international.tracking_number,
                'tracking_url': international.tracking_url
            })
        except Exception as e:
            logger.error(f"Erreur mise à jour suivi: {e}")
            return self.error_response("Erreur lors de la mise à jour du suivi")
    
    def _submit_documents(self, transaction_obj, request):
        """Soumettre des documents internationaux"""
        try:
            international = transaction_obj.international_details
            international.invoice_number = request.data.get('invoice_number', international.invoice_number)
            international.certificate_number = request.data.get('certificate_number', international.certificate_number)
            international.bill_of_lading = request.data.get('bill_of_lading', international.bill_of_lading)
            international.save()
            
            return self.success_response({
                'message': 'Documents soumis avec succès',
                'documents': {
                    'invoice_number': international.invoice_number,
                    'certificate_number': international.certificate_number,
                    'bill_of_lading': international.bill_of_lading
                }
            })
        except Exception as e:
            logger.error(f"Erreur soumission documents: {e}")
            return self.error_response("Erreur lors de la soumission des documents")
    
    def _extend_inspection(self, transaction_obj, request):
        """Prolonger la période d'inspection"""
        try:
            international = transaction_obj.international_details
            additional_days = request.data.get('additional_days', 2)
            
            if international.inspection_deadline:
                international.inspection_deadline += timezone.timedelta(days=additional_days)
            else:
                international.inspection_deadline = timezone.now() + timezone.timedelta(days=additional_days)
            
            international.save()
            
            return self.success_response({
                'message': f'Période d\'inspection prolongée de {additional_days} jours',
                'new_deadline': international.inspection_deadline.strftime("%d/%m/%Y %H:%M")
            })
        except Exception as e:
            logger.error(f"Erreur prolongation inspection: {e}")
            return self.error_response("Erreur lors de la prolongation de la période d'inspection")