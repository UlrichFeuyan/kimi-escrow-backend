from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count
import logging

from .models import Dispute, DisputeEvidence, DisputeComment
from .serializers import DisputeSerializer, DisputeEvidenceSerializer, DisputeCommentSerializer
from core.permissions import IsAdmin, IsArbitre, IsAdminOrArbitre, IsTransactionParticipant
from core.utils import APIResponseMixin

User = get_user_model()
logger = logging.getLogger(__name__)


class DisputeListCreateView(generics.ListCreateAPIView, APIResponseMixin):
    """Liste et création de litiges"""
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'ADMIN':
            return Dispute.objects.all()
        elif user.role == 'ARBITRE':
            return Dispute.objects.filter(
                Q(arbitre=user) | Q(status='OPEN')
            )
        else:
            return Dispute.objects.filter(
                Q(complainant=user) | Q(respondent=user)
            )
    
    def perform_create(self, serializer):
        # L'utilisateur devient automatiquement le plaignant
        dispute = serializer.save(complainant=self.request.user)
        
        # Déterminer le défendeur
        transaction = dispute.transaction
        if self.request.user == transaction.buyer:
            dispute.respondent = transaction.seller
        else:
            dispute.respondent = transaction.buyer
        dispute.save()


class DisputeDetailView(generics.RetrieveUpdateAPIView, APIResponseMixin):
    """Détail d'un litige"""
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['ADMIN', 'ARBITRE']:
            return Dispute.objects.all()
        else:
            return Dispute.objects.filter(
                Q(complainant=user) | Q(respondent=user)
            )


class AssignArbitreView(APIView, APIResponseMixin):
    """Assigner un arbitre à un litige"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def post(self, request, pk):
        try:
            dispute = Dispute.objects.get(pk=pk)
        except Dispute.DoesNotExist:
            return self.error_response("Litige non trouvé", status_code=404)
        
        arbitre_id = request.data.get('arbitre_id')
        if not arbitre_id:
            return self.error_response("ID de l'arbitre requis")
        
        try:
            arbitre = User.objects.get(id=arbitre_id, role='ARBITRE')
        except User.DoesNotExist:
            return self.error_response("Arbitre non trouvé")
        
        if not dispute.can_be_assigned_to(arbitre):
            return self.error_response("Cet arbitre ne peut pas être assigné à ce litige")
        
        dispute.assign_arbitre(arbitre)
        
        return self.success_response({
            'message': f'Litige assigné à {arbitre.get_full_name()}',
            'dispute': DisputeSerializer(dispute).data
        })


class ResolveDisputeView(APIView, APIResponseMixin):
    """Résoudre un litige"""
    permission_classes = [permissions.IsAuthenticated, IsArbitre]
    
    def post(self, request, pk):
        try:
            dispute = Dispute.objects.get(pk=pk, arbitre=request.user)
        except Dispute.DoesNotExist:
            return self.error_response("Litige non trouvé ou non assigné à vous", status_code=404)
        
        verdict = request.data.get('verdict')
        resolution_notes = request.data.get('resolution_notes')
        refund_amount = request.data.get('refund_amount')
        
        if not verdict or not resolution_notes:
            return self.error_response("Verdict et notes de résolution requis")
        
        dispute.resolve(verdict, resolution_notes, refund_amount)
        
        return self.success_response({
            'message': 'Litige résolu avec succès',
            'dispute': DisputeSerializer(dispute).data
        })


class DisputeEvidenceCreateView(generics.CreateAPIView, APIResponseMixin):
    """Ajouter une preuve à un litige"""
    serializer_class = DisputeEvidenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        dispute_id = self.kwargs['dispute_id']
        dispute = Dispute.objects.get(id=dispute_id)
        
        # Vérifier que l'utilisateur peut soumettre des preuves
        if self.request.user not in [dispute.complainant, dispute.respondent, dispute.arbitre]:
            raise permissions.PermissionDenied("Vous ne pouvez pas soumettre de preuves pour ce litige")
        
        serializer.save(dispute=dispute, submitted_by=self.request.user)


class DisputeCommentListCreateView(generics.ListCreateAPIView, APIResponseMixin):
    """Commentaires d'un litige"""
    serializer_class = DisputeCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        dispute_id = self.kwargs['dispute_id']
        queryset = DisputeComment.objects.filter(dispute_id=dispute_id)
        
        # Les commentaires internes ne sont visibles que par les arbitres et admins
        if self.request.user.role not in ['ADMIN', 'ARBITRE']:
            queryset = queryset.filter(is_internal=False)
        
        return queryset.order_by('created_at')
    
    def perform_create(self, serializer):
        dispute_id = self.kwargs['dispute_id']
        dispute = Dispute.objects.get(id=dispute_id)
        
        # Vérifier que l'utilisateur peut commenter
        allowed_users = [dispute.complainant, dispute.respondent]
        if dispute.arbitre:
            allowed_users.append(dispute.arbitre)
        
        if self.request.user not in allowed_users and self.request.user.role != 'ADMIN':
            raise permissions.PermissionDenied("Vous ne pouvez pas commenter ce litige")
        
        serializer.save(dispute=dispute, author=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminOrArbitre])
def dispute_statistics(request):
    """Statistiques des litiges"""
    from django.db.models import Avg
    from datetime import timedelta
    
    now = timezone.now()
    last_month = now - timedelta(days=30)
    
    stats = {
        'total_disputes': Dispute.objects.count(),
        'open_disputes': Dispute.objects.filter(status='OPEN').count(),
        'resolved_disputes': Dispute.objects.filter(status='RESOLVED').count(),
        'disputes_this_month': Dispute.objects.filter(created_at__gte=last_month).count(),
        'disputes_by_category': dict(
            Dispute.objects.values('category').annotate(count=Count('category')).values_list('category', 'count')
        ),
        'disputes_by_status': dict(
            Dispute.objects.values('status').annotate(count=Count('status')).values_list('status', 'count')
        ),
        'average_resolution_time_days': 0,  # À calculer
    }
    
    return Response({
        'success': True,
        'data': stats,
        'timestamp': now.isoformat()
    })