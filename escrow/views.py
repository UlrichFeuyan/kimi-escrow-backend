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