import json
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock
from .models import Payment, PaymentMethod
from users.models import UserProfile
from escrow.models import EscrowTransaction

User = get_user_model()


class MobileMoneyPaymentTestCase(APITestCase):
    """Tests pour les paiements Mobile Money"""
    
    def setUp(self):
        self.client = APIClient()
        self.collect_url = reverse('momo-collect')
        
        # Créer des utilisateurs
        self.buyer = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='John',
            last_name='Buyer',
            is_phone_verified=True
        )
        self.buyer_profile = UserProfile.objects.create(
            user=self.buyer,
            role='BUYER',
            kyc_status='VERIFIED'
        )
        
        self.seller = User.objects.create_user(
            phone_number='+237698765432',
            password='TestPassword123!',
            first_name='Jane',
            last_name='Seller',
            is_phone_verified=True
        )
        self.seller_profile = UserProfile.objects.create(
            user=self.seller,
            role='SELLER',
            kyc_status='VERIFIED'
        )
        
        # Créer une transaction escrow
        self.transaction = EscrowTransaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            title='Test Transaction',
            description='Test description',
            category='GOODS',
            amount=100000,
            delivery_address='Test Address',
            status='PAYMENT_PENDING'
        )
        
        # Authentifier l'acheteur
        refresh = RefreshToken.for_user(self.buyer)
        self.buyer_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')
    
    @patch('payments.services.MTNMoMoService.request_to_pay')
    def test_mtn_momo_collection_success(self, mock_request_to_pay):
        """Test de collecte MTN Mobile Money réussie"""
        mock_request_to_pay.return_value = {
            'success': True,
            'reference_id': 'MTN-12345-ABCDE',
            'external_id': 'EXT-67890',
            'status': 'PENDING'
        }
        
        payment_data = {
            'transaction_id': self.transaction.id,
            'phone_number': '+237612345678',
            'provider': 'MTN_MOMO',
            'amount': 100000
        }
        
        response = self.client.post(self.collect_url, payment_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Vérifier que le paiement a été créé
        payment = Payment.objects.get(transaction=self.transaction)
        self.assertEqual(payment.amount, Decimal('100000'))
        self.assertEqual(payment.provider, 'MTN_MOMO')
        self.assertEqual(payment.status, 'PENDING')
        self.assertEqual(payment.reference, 'MTN-12345-ABCDE')
