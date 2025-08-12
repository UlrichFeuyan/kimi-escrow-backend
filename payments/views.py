from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
import logging

from .models import Payment, PaymentMethod, Webhook
from .serializers import PaymentSerializer, PaymentMethodSerializer
from core.utils import APIResponseMixin
from core.permissions import IsKYCVerified

User = get_user_model()
logger = logging.getLogger(__name__)


class MobileMoneyCollectionView(APIView, APIResponseMixin):
    """Initier une collecte Mobile Money"""
    permission_classes = [permissions.IsAuthenticated, IsKYCVerified]
    
    def post(self, request):
        # Logique de collecte Mobile Money
        return self.success_response({
            'message': 'Collecte Mobile Money initiée',
            'reference': 'PAY-123456'
        })


class PaymentStatusView(APIView, APIResponseMixin):
    """Vérifier le statut d'un paiement"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, reference):
        try:
            payment = Payment.objects.get(reference=reference, user=request.user)
            return self.success_response({
                'reference': payment.reference,
                'status': payment.status,
                'amount': payment.amount
            })
        except Payment.DoesNotExist:
            return self.error_response("Paiement non trouvé", status_code=404)


class PaymentMethodListView(generics.ListAPIView):
    """Liste des méthodes de paiement disponibles"""
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(status='ACTIVE')


class PaymentHistoryView(generics.ListAPIView):
    """Historique des paiements de l'utilisateur"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')


@method_decorator(csrf_exempt, name='dispatch')
class MTNWebhookView(APIView):
    """Webhook MTN Mobile Money"""
    permission_classes = []
    
    def post(self, request):
        # Traitement webhook MTN
        return Response({'status': 'success'}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class OrangeWebhookView(APIView):
    """Webhook Orange Money"""
    permission_classes = []
    
    def post(self, request):
        # Traitement webhook Orange
        return Response({'status': 'success'}, status=200)