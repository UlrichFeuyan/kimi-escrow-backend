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
from .models import EscrowTransaction, TransactionMessage, TransactionAction
from users.models import UserProfile
from payments.models import Payment

User = get_user_model()


class EscrowTransactionTestCase(APITestCase):
    """Tests pour les endpoints de transactions escrow"""
    
    def setUp(self):
        self.client = APIClient()
        self.transactions_url = reverse('transaction-list-create')
        
        # Créer un acheteur
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
        
        # Créer un vendeur
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
        
        # Authentifier l'acheteur par défaut
        refresh = RefreshToken.for_user(self.buyer)
        self.buyer_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')
        
        # Données de transaction de test
        self.transaction_data = {
            'title': 'Vente iPhone 13',
            'description': 'iPhone 13 Pro Max 256GB, état neuf',
            'category': 'GOODS',
            'amount': 450000,
            'seller_phone': self.seller.phone_number,
            'payment_deadline': (timezone.now() + timedelta(days=3)).isoformat(),
            'delivery_deadline': (timezone.now() + timedelta(days=7)).isoformat(),
            'delivery_address': 'Douala, Cameroun'
        }
    
    def test_create_transaction_success(self):
        """Test de création de transaction réussie"""
        response = self.client.post(self.transactions_url, self.transaction_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Vérifier que la transaction a été créée
        transaction = EscrowTransaction.objects.get(id=response.data['data']['id'])
        self.assertEqual(transaction.title, self.transaction_data['title'])
        self.assertEqual(transaction.buyer, self.buyer)
        self.assertEqual(transaction.seller, self.seller)
        self.assertEqual(transaction.status, 'PENDING')
        self.assertEqual(str(transaction.amount), str(self.transaction_data['amount']))
    
    def test_create_transaction_invalid_seller(self):
        """Test de création avec vendeur inexistant"""
        invalid_data = self.transaction_data.copy()
        invalid_data['seller_phone'] = '+237999999999'
        
        response = self.client.post(self.transactions_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('seller_phone', response.data['errors'])
