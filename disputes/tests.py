import json
from io import BytesIO
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock
from .models import Dispute, DisputeEvidence, DisputeComment
from escrow.models import EscrowTransaction
from users.models import UserProfile

User = get_user_model()


class DisputeTestCase(APITestCase):
    """Tests pour les endpoints de litiges"""
    
    def setUp(self):
        self.client = APIClient()
        self.disputes_url = reverse('dispute-list-create')
        
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
            description='Transaction avec problème',
            category='GOODS',
            amount=100000,
            delivery_address='Test Address',
            status='DELIVERED'
        )
        
        # Authentifier l'acheteur par défaut
        refresh = RefreshToken.for_user(self.buyer)
        self.buyer_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}')
    
    def test_create_dispute_success(self):
        """Test de création de litige réussie"""
        dispute_data = {
            'transaction': self.transaction.id,
            'reason': 'PRODUCT_NOT_AS_DESCRIBED',
            'description': 'Le produit reçu ne correspond pas à la description.',
            'amount_disputed': 50000
        }
        
        response = self.client.post(self.disputes_url, dispute_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Vérifier que le litige a été créé
        dispute = Dispute.objects.get(id=response.data['data']['id'])
        self.assertEqual(dispute.transaction, self.transaction)
        self.assertEqual(dispute.plaintiff, self.buyer)
        self.assertEqual(dispute.defendant, self.seller)
        self.assertEqual(dispute.reason, 'PRODUCT_NOT_AS_DESCRIBED')
        self.assertEqual(dispute.status, 'OPEN')
        self.assertEqual(dispute.amount_disputed, 50000)
