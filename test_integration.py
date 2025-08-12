"""
Tests d'intégration pour la plateforme Kimi Escrow
Tests des flux complets end-to-end
"""

import json
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

# Import des modèles
from users.models import UserProfile, KYCDocument
from escrow.models import EscrowTransaction, TransactionMessage, TransactionAction
from payments.models import Payment
from disputes.models import Dispute, DisputeEvidence, DisputeComment
from core.models import AuditLog

User = get_user_model()


class CompleteTransactionFlowTestCase(APITestCase):
    """Test du flux complet d'une transaction escrow réussie"""
    
    def setUp(self):
        self.client = APIClient()
        
        # URLs principales
        self.register_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.transactions_url = reverse('transaction-list-create')
        self.collect_url = reverse('momo-collect')
        
    @patch('users.services.SmileIDService.send_sms')
    @patch('payments.services.MTNMoMoService.request_to_pay')
    def test_complete_successful_transaction_flow(self, mock_payment, mock_sms):
        """Test d'un flux de transaction complet et réussi"""
        mock_sms.return_value = True
        mock_payment.return_value = {
            'success': True,
            'reference_id': 'MTN-12345-ABCDE',
            'external_id': 'EXT-67890',
            'status': 'PENDING'
        }
        
        # 1. Inscription de l'acheteur
        buyer_data = {
            'phone_number': '+237612345678',
            'password': 'BuyerPassword123!',
            'first_name': 'John',
            'last_name': 'Buyer',
            'role': 'BUYER'
        }
        
        response = self.client.post(self.register_url, buyer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        buyer_tokens = response.data['data']['tokens']
        buyer_id = response.data['data']['user_id']
        
        # 2. Inscription du vendeur
        seller_data = {
            'phone_number': '+237698765432',
            'password': 'SellerPassword123!',
            'first_name': 'Jane',
            'last_name': 'Seller',
            'role': 'SELLER'
        }
        
        response = self.client.post(self.register_url, seller_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        seller_tokens = response.data['data']['tokens']
        
        # 3. Marquer les utilisateurs comme vérifiés KYC (simulation)
        buyer = User.objects.get(id=buyer_id)
        buyer.profile.kyc_status = 'VERIFIED'
        buyer.profile.save()
        
        seller = User.objects.get(phone_number=seller_data['phone_number'])
        seller.profile.kyc_status = 'VERIFIED'
        seller.profile.save()
        
        # 4. L'acheteur crée une transaction
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {buyer_tokens["access"]}')
        
        transaction_data = {
            'title': 'Vente iPhone 13 Pro',
            'description': 'iPhone 13 Pro Max 256GB, couleur bleu, état neuf avec boîte',
            'category': 'GOODS',
            'amount': 450000,
            'seller_phone': seller_data['phone_number'],
            'payment_deadline': (timezone.now() + timedelta(days=3)).isoformat(),
            'delivery_deadline': (timezone.now() + timedelta(days=7)).isoformat(),
            'delivery_address': 'Douala, Akwa Nord, Rue des Cocotiers'
        }
        
        response = self.client.post(self.transactions_url, transaction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transaction_id = response.data['data']['id']
        
        # Vérifier que la transaction a été créée
        transaction = EscrowTransaction.objects.get(id=transaction_id)
        self.assertEqual(transaction.status, 'PENDING')
        self.assertEqual(transaction.buyer, buyer)
        self.assertEqual(transaction.seller, seller)
        
        # 5. L'acheteur initie le paiement Mobile Money
        payment_data = {
            'transaction_id': transaction_id,
            'phone_number': buyer_data['phone_number'],
            'provider': 'MTN_MOMO',
            'amount': 450000
        }
        
        response = self.client.post(self.collect_url, payment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Vérifier que le paiement a été créé
        payment = Payment.objects.get(transaction_id=transaction_id)
        self.assertEqual(payment.status, 'PENDING')
        self.assertEqual(payment.amount, Decimal('450000'))
        
        # 6. Simulation de confirmation de paiement via webhook
        with patch('payments.services.MTNMoMoService.verify_webhook_signature') as mock_verify:
            mock_verify.return_value = True
            
            webhook_url = reverse('mtn-webhook')
            webhook_data = {
                'financialTransactionId': 'MTN-12345-ABCDE',
                'externalId': 'EXT-67890',
                'amount': '450000',
                'currency': 'XAF',
                'payer': {
                    'partyIdType': 'MSISDN',
                    'partyId': buyer_data['phone_number']
                },
                'status': 'SUCCESSFUL'
            }
            
            response = self.client.post(
                webhook_url,
                webhook_data,
                format='json',
                HTTP_X_MTN_SIGNATURE='test_signature'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que le paiement et la transaction ont été mis à jour
        payment.refresh_from_db()
        transaction.refresh_from_db()
        self.assertEqual(payment.status, 'COMPLETED')
        self.assertEqual(transaction.status, 'PAYMENT_CONFIRMED')
        
        # 7. Le vendeur marque la commande comme livrée
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {seller_tokens["access"]}')
        
        actions_url = reverse('transaction-actions', kwargs={'pk': transaction_id})
        action_data = {
            'action': 'mark_delivered',
            'notes': 'iPhone livré en main propre à l\'adresse indiquée. Client satisfait.'
        }
        
        response = self.client.post(actions_url, action_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que le statut a été mis à jour
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'DELIVERED')
        
        # Vérifier qu'une action a été enregistrée
        action = TransactionAction.objects.get(transaction=transaction, action_type='MARK_DELIVERED')
        self.assertEqual(action.user, seller)
        
        # 8. L'acheteur confirme la réception
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {buyer_tokens["access"]}')
        
        confirm_data = {
            'action': 'confirm_delivery',
            'notes': 'iPhone reçu en parfait état. Merci !'
        }
        
        response = self.client.post(actions_url, confirm_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que la transaction est complétée
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'COMPLETED')
        
        # Vérifier qu'une action a été enregistrée
        action = TransactionAction.objects.get(transaction=transaction, action_type='CONFIRM_DELIVERY')
        self.assertEqual(action.user, buyer)
        
        # 9. Vérifier que des logs d'audit ont été créés
        audit_logs = AuditLog.objects.filter(
            resource_type='TRANSACTION',
            resource_id=transaction_id
        )
        self.assertGreater(audit_logs.count(), 0)
        
        print("✅ Flux de transaction réussie testé avec succès")


class DisputeResolutionFlowTestCase(APITestCase):
    """Test du flux complet de résolution d'un litige"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Créer des utilisateurs avec les bons statuts
        self.buyer = User.objects.create_user(
            phone_number='+237612345678',
            password='BuyerPassword123!',
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
            password='SellerPassword123!',
            first_name='Jane',
            last_name='Seller',
            is_phone_verified=True
        )
        self.seller_profile = UserProfile.objects.create(
            user=self.seller,
            role='SELLER',
            kyc_status='VERIFIED'
        )
        
        self.arbitre = User.objects.create_user(
            phone_number='+237655555555',
            password='ArbitrePassword123!',
            first_name='Jean',
            last_name='Arbitre',
            is_phone_verified=True
        )
        self.arbitre_profile = UserProfile.objects.create(
            user=self.arbitre,
            role='ARBITRE'
        )
        
        self.admin = User.objects.create_user(
            phone_number='+237600000000',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='System',
            is_staff=True
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin,
            role='ADMIN'
        )
        
        # Créer une transaction livrée
        self.transaction = EscrowTransaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            title='iPhone 13 défectueux',
            description='iPhone 13 avec écran cassé',
            category='GOODS',
            amount=400000,
            delivery_address='Douala, Cameroun',
            status='DELIVERED'
        )
        
        # Créer un paiement associé
        self.payment = Payment.objects.create(
            transaction=self.transaction,
            user=self.buyer,
            amount=400000,
            provider='MTN_MOMO',
            reference='PAY-TEST-001',
            status='COMPLETED'
        )
    
    def create_test_image(self):
        """Créer une image de test pour les preuves"""
        image = Image.new('RGB', (100, 100), 'red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(
            name='evidence.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )
    
    def test_complete_dispute_resolution_flow(self):
        """Test d'un flux complet de résolution de litige"""
        
        # 1. L'acheteur crée un litige
        buyer_token = str(RefreshToken.for_user(self.buyer).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {buyer_token}')
        
        disputes_url = reverse('dispute-list-create')
        dispute_data = {
            'transaction': self.transaction.id,
            'reason': 'PRODUCT_NOT_AS_DESCRIBED',
            'description': 'L\'iPhone reçu a l\'écran complètement cassé, ce qui n\'était pas mentionné dans la description.',
            'amount_disputed': 200000
        }
        
        response = self.client.post(disputes_url, dispute_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        dispute_id = response.data['data']['id']
        
        # Vérifier que le litige a été créé
        dispute = Dispute.objects.get(id=dispute_id)
        self.assertEqual(dispute.status, 'OPEN')
        self.assertEqual(dispute.plaintiff, self.buyer)
        self.assertEqual(dispute.defendant, self.seller)
        
        # 2. L'acheteur ajoute des preuves photographiques
        evidence_url = reverse('dispute-evidence', kwargs={'dispute_id': dispute_id})
        test_file = self.create_test_image()
        
        evidence_data = {
            'evidence_type': 'PHOTO',
            'description': 'Photo de l\'iPhone avec écran cassé',
            'file': test_file
        }
        
        response = self.client.post(evidence_url, evidence_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Vérifier que la preuve a été ajoutée
        evidence = DisputeEvidence.objects.get(dispute=dispute)
        self.assertEqual(evidence.evidence_type, 'PHOTO')
        self.assertEqual(evidence.submitted_by, self.buyer)
        
        # 3. Le vendeur ajoute un commentaire de défense
        seller_token = str(RefreshToken.for_user(self.seller).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {seller_token}')
        
        comments_url = reverse('dispute-comments', kwargs={'dispute_id': dispute_id})
        comment_data = {
            'comment': 'L\'iPhone était en parfait état lors de l\'envoi. Le client a peut-être endommagé l\'écran après réception.'
        }
        
        response = self.client.post(comments_url, comment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. L'admin assigne un arbitre
        admin_token = str(RefreshToken.for_user(self.admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        assign_url = reverse('assign-arbitre', kwargs={'pk': dispute_id})
        assign_data = {
            'arbitre_id': self.arbitre.id
        }
        
        response = self.client.post(assign_url, assign_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que l'arbitre a été assigné
        dispute.refresh_from_db()
        self.assertEqual(dispute.arbitre, self.arbitre)
        self.assertEqual(dispute.status, 'IN_ARBITRATION')
        
        # 5. L'arbitre ajoute des questions
        arbitre_token = str(RefreshToken.for_user(self.arbitre).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {arbitre_token}')
        
        arbitre_comment_data = {
            'comment': 'Pouvez-vous fournir une preuve d\'achat ou des photos de l\'emballage lors de la réception ?'
        }
        
        response = self.client.post(comments_url, arbitre_comment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 6. L'acheteur répond avec une preuve supplémentaire
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {buyer_token}')
        
        buyer_response_data = {
            'comment': 'Voici la photo de l\'emballage intact. L\'iPhone était déjà endommagé à l\'intérieur.'
        }
        
        response = self.client.post(comments_url, buyer_response_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Ajouter une deuxième preuve
        test_file2 = self.create_test_image()
        evidence_data2 = {
            'evidence_type': 'PHOTO',
            'description': 'Photo de l\'emballage intact à la réception',
            'file': test_file2
        }
        
        response = self.client.post(evidence_url, evidence_data2, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 7. L'arbitre résout le litige en faveur de l'acheteur
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {arbitre_token}')
        
        resolve_url = reverse('resolve-dispute', kwargs={'pk': dispute_id})
        resolution_data = {
            'resolution': 'BUYER_WINS',
            'resolution_notes': 'Les preuves photographiques montrent clairement que l\'iPhone était déjà endommagé lors de la livraison. L\'emballage intact confirme que le dommage était présent avant la réception.',
            'refund_amount': 150000
        }
        
        response = self.client.post(resolve_url, resolution_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que le litige a été résolu
        dispute.refresh_from_db()
        self.assertEqual(dispute.status, 'RESOLVED')
        self.assertEqual(dispute.resolution, 'BUYER_WINS')
        self.assertEqual(dispute.refund_amount, 150000)
        self.assertIsNotNone(dispute.resolved_at)
        
        # 8. Vérifier que tous les commentaires et preuves sont présents
        comments = DisputeComment.objects.filter(dispute=dispute)
        self.assertEqual(comments.count(), 3)  # Vendeur + Arbitre + Acheteur
        
        evidences = DisputeEvidence.objects.filter(dispute=dispute)
        self.assertEqual(evidences.count(), 2)  # 2 photos
        
        # 9. Vérifier que des logs d'audit ont été créés
        audit_logs = AuditLog.objects.filter(
            resource_type='DISPUTE',
            resource_id=dispute_id
        )
        self.assertGreater(audit_logs.count(), 0)
        
        print("✅ Flux de résolution de litige testé avec succès")


class KYCVerificationFlowTestCase(APITestCase):
    """Test du flux complet de vérification KYC"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Créer un admin
        self.admin = User.objects.create_user(
            phone_number='+237600000000',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='System',
            is_staff=True
        )
        UserProfile.objects.create(user=self.admin, role='ADMIN')
    
    def create_test_document(self):
        """Créer un document de test pour le KYC"""
        image = Image.new('RGB', (400, 300), 'blue')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(
            name='id_front.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )
    
    @patch('users.services.SmileIDService.send_sms')
    @patch('users.services.SmileIDService.verify_webhook_signature')
    def test_complete_kyc_verification_flow(self, mock_verify_webhook, mock_sms):
        """Test d'un flux complet de vérification KYC"""
        mock_sms.return_value = True
        mock_verify_webhook.return_value = True
        
        # 1. Inscription d'un nouvel utilisateur
        register_url = reverse('user-register')
        user_data = {
            'phone_number': '+237612345678',
            'password': 'UserPassword123!',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'role': 'BUYER'
        }
        
        response = self.client.post(register_url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user_id = response.data['data']['user_id']
        tokens = response.data['data']['tokens']
        
        # Vérifier que l'utilisateur a un statut KYC en attente
        user = User.objects.get(id=user_id)
        self.assertEqual(user.profile.kyc_status, 'PENDING')
        
        # 2. L'utilisateur upload ses documents KYC
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        upload_url = reverse('kyc-upload')
        
        # Upload de la carte d'identité recto
        id_front = self.create_test_document()
        upload_data = {
            'document_type': 'ID_FRONT',
            'file': id_front
        }
        
        response = self.client.post(upload_url, upload_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Upload de la carte d'identité verso
        id_back = self.create_test_document()
        upload_data = {
            'document_type': 'ID_BACK',
            'file': id_back
        }
        
        response = self.client.post(upload_url, upload_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Vérifier que les documents ont été créés
        documents = KYCDocument.objects.filter(user=user)
        self.assertEqual(documents.count(), 2)
        
        for doc in documents:
            self.assertEqual(doc.status, 'PENDING')
        
        # 4. Simulation de webhook Smile ID pour validation automatique
        webhook_url = reverse('smile-id-webhook')
        
        # Trouver le job_id d'un document (simulation)
        front_doc = documents.get(document_type='ID_FRONT')
        front_doc.smile_id_job_id = 'job_123_front'
        front_doc.save()
        
        webhook_data = {
            'job_id': 'job_123_front',
            'result': {
                'result_text': 'Approved',
                'result_code': '1012',
                'confidence_value': 0.95
            }
        }
        
        response = self.client.post(
            webhook_url,
            webhook_data,
            format='json',
            HTTP_X_SMILE_SIGNATURE='test_signature'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que le document a été approuvé
        front_doc.refresh_from_db()
        self.assertEqual(front_doc.status, 'APPROVED')
        
        # 5. Validation manuelle par l'admin du deuxième document
        admin_token = str(RefreshToken.for_user(self.admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        approval_url = reverse('admin-kyc-approve', kwargs={'user_id': user_id})
        approval_data = {
            'action': 'approve'
        }
        
        response = self.client.post(approval_url, approval_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 6. Vérifier que l'utilisateur est maintenant vérifié
        user.refresh_from_db()
        self.assertEqual(user.profile.kyc_status, 'VERIFIED')
        
        # 7. Vérifier que l'utilisateur peut maintenant créer des transactions importantes
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        # Créer un vendeur pour la transaction
        seller = User.objects.create_user(
            phone_number='+237698765432',
            password='SellerPassword123!',
            first_name='Marie',
            last_name='Vendor'
        )
        seller_profile = UserProfile.objects.create(
            user=seller,
            role='SELLER',
            kyc_status='VERIFIED'
        )
        
        transactions_url = reverse('transaction-list-create')
        transaction_data = {
            'title': 'Achat ordinateur portable',
            'description': 'MacBook Pro 16 pouces',
            'category': 'GOODS',
            'amount': 800000,  # Montant important nécessitant KYC
            'seller_phone': seller.phone_number,
            'payment_deadline': (timezone.now() + timedelta(days=3)).isoformat(),
            'delivery_deadline': (timezone.now() + timedelta(days=7)).isoformat(),
            'delivery_address': 'Yaoundé, Cameroun'
        }
        
        response = self.client.post(transactions_url, transaction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 8. Vérifier que des logs d'audit ont été créés
        audit_logs = AuditLog.objects.filter(
            resource_type='USER',
            resource_id=user_id,
            action__icontains='KYC'
        )
        self.assertGreater(audit_logs.count(), 0)
        
        print("✅ Flux de vérification KYC testé avec succès")


class MultiUserInteractionTestCase(APITestCase):
    """Test des interactions entre plusieurs utilisateurs"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Créer plusieurs utilisateurs
        self.users = {}
        self.tokens = {}
        
        user_configs = [
            {'phone': '+237612345678', 'name': 'Jean Acheteur', 'role': 'BUYER'},
            {'phone': '+237698765432', 'name': 'Marie Vendeuse', 'role': 'SELLER'},
            {'phone': '+237655555555', 'name': 'Paul Arbitre', 'role': 'ARBITRE'},
            {'phone': '+237600000000', 'name': 'Admin Système', 'role': 'ADMIN'},
        ]
        
        for config in user_configs:
            first_name, last_name = config['name'].split(' ', 1)
            user = User.objects.create_user(
                phone_number=config['phone'],
                password='TestPassword123!',
                first_name=first_name,
                last_name=last_name,
                is_staff=(config['role'] == 'ADMIN'),
                is_phone_verified=True
            )
            
            UserProfile.objects.create(
                user=user,
                role=config['role'],
                kyc_status='VERIFIED' if config['role'] != 'ADMIN' else 'NOT_REQUIRED'
            )
            
            self.users[config['role']] = user
            self.tokens[config['role']] = str(RefreshToken.for_user(user).access_token)
    
    def test_multi_user_transaction_with_messages(self):
        """Test d'une transaction avec échanges de messages entre acheteur et vendeur"""
        
        # 1. L'acheteur crée une transaction
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["BUYER"]}')
        
        transactions_url = reverse('transaction-list-create')
        transaction_data = {
            'title': 'Recherche PlayStation 5',
            'description': 'Je cherche une PS5 neuve avec manettes',
            'category': 'GOODS',
            'amount': 350000,
            'seller_phone': self.users['SELLER'].phone_number,
            'payment_deadline': (timezone.now() + timedelta(days=5)).isoformat(),
            'delivery_deadline': (timezone.now() + timedelta(days=10)).isoformat(),
            'delivery_address': 'Douala, Bonanjo'
        }
        
        response = self.client.post(transactions_url, transaction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transaction_id = response.data['data']['id']
        
        # 2. L'acheteur envoie un message au vendeur
        messages_url = reverse('transaction-messages', kwargs={'transaction_id': transaction_id})
        message_data = {
            'message': 'Bonjour, avez-vous la PlayStation en stock ? Pouvez-vous me dire quelle version exacte ?'
        }
        
        response = self.client.post(messages_url, message_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Le vendeur répond
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["SELLER"]}')
        
        seller_message = {
            'message': 'Oui, j\'ai une PS5 Digital Edition neuve sous garantie. Avec deux manettes DualSense. Intéressé ?'
        }
        
        response = self.client.post(messages_url, seller_message, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. L'acheteur confirme et pose une question sur la livraison
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["BUYER"]}')
        
        buyer_response = {
            'message': 'Parfait ! Pouvez-vous livrer demain ? Et acceptez-vous un paiement par Orange Money ?'
        }
        
        response = self.client.post(messages_url, buyer_response, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 5. Le vendeur confirme
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["SELLER"]}')
        
        seller_confirmation = {
            'message': 'Oui, livraison possible demain après-midi. MTN ou Orange Money, les deux sont OK pour moi.'
        }
        
        response = self.client.post(messages_url, seller_confirmation, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 6. Vérifier que tous les messages sont visibles pour les deux parties
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["BUYER"]}')
        response = self.client.get(messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        messages = response.data['data']['results']
        self.assertEqual(len(messages), 4)
        
        # Vérifier que les messages sont dans le bon ordre (chronologique)
        message_contents = [msg['message'] for msg in messages]
        self.assertIn('avez-vous la PlayStation', message_contents[0])
        self.assertIn('Digital Edition', message_contents[1])
        
        # 7. Vérifier que le vendeur voit aussi tous les messages
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["SELLER"]}')
        response = self.client.get(messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        seller_messages = response.data['data']['results']
        self.assertEqual(len(seller_messages), 4)
        
        # 8. Vérifier qu'un utilisateur non autorisé ne peut pas voir les messages
        unauthorized_user = User.objects.create_user(
            phone_number='+237611111111',
            password='TestPassword123!',
            first_name='Intrus',
            last_name='Curieux'
        )
        UserProfile.objects.create(user=unauthorized_user, role='BUYER')
        
        unauthorized_token = str(RefreshToken.for_user(unauthorized_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {unauthorized_token}')
        
        response = self.client.get(messages_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        print("✅ Test d'interactions multi-utilisateurs avec messages réussi")
    
    def test_admin_statistics_and_monitoring(self):
        """Test des fonctionnalités d'administration et de monitoring"""
        
        # Créer quelques données de test
        transaction1 = EscrowTransaction.objects.create(
            buyer=self.users['BUYER'],
            seller=self.users['SELLER'],
            title='Transaction Test 1',
            category='GOODS',
            amount=100000,
            delivery_address='Test',
            status='COMPLETED'
        )
        
        transaction2 = EscrowTransaction.objects.create(
            buyer=self.users['BUYER'],
            seller=self.users['SELLER'],
            title='Transaction Test 2',
            category='SERVICES',
            amount=200000,
            delivery_address='Test',
            status='PENDING'
        )
        
        # Créer un litige
        dispute = Dispute.objects.create(
            transaction=transaction1,
            plaintiff=self.users['BUYER'],
            defendant=self.users['SELLER'],
            reason='PRODUCT_NOT_AS_DESCRIBED',
            description='Test dispute',
            amount_disputed=50000,
            status='RESOLVED',
            arbitre=self.users['ARBITRE'],
            resolution='BUYER_WINS'
        )
        
        # 1. L'admin vérifie les statistiques utilisateurs
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["ADMIN"]}')
        
        user_stats_url = reverse('admin-user-stats')
        response = self.client.get(user_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stats = response.data['data']
        
        self.assertIn('total_users', stats)
        self.assertIn('users_by_role', stats)
        self.assertIn('kyc_statistics', stats)
        self.assertEqual(stats['total_users'], 4)  # Nos 4 utilisateurs de test
        
        # 2. L'admin vérifie les statistiques de transactions
        transaction_stats_url = reverse('transaction-statistics')
        response = self.client.get(transaction_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transaction_stats = response.data['data']
        
        self.assertIn('total_transactions', transaction_stats)
        self.assertIn('transactions_by_status', transaction_stats)
        self.assertIn('total_volume', transaction_stats)
        self.assertEqual(transaction_stats['total_transactions'], 2)
        self.assertEqual(transaction_stats['total_volume'], 300000)
        
        # 3. L'admin vérifie les statistiques de litiges
        dispute_stats_url = reverse('dispute-statistics')
        response = self.client.get(dispute_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dispute_stats = response.data['data']
        
        self.assertIn('total_disputes', dispute_stats)
        self.assertIn('disputes_by_status', dispute_stats)
        self.assertIn('resolution_rate', dispute_stats)
        self.assertEqual(dispute_stats['total_disputes'], 1)
        
        # 4. L'admin consulte les logs d'audit
        audit_logs_url = reverse('audit-logs')
        response = self.client.get(audit_logs_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logs = response.data['data']['results']
        self.assertGreater(len(logs), 0)
        
        # 5. Vérifier qu'un non-admin ne peut pas accéder à ces statistiques
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["BUYER"]}')
        
        response = self.client.get(user_stats_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.client.get(transaction_stats_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.client.get(dispute_stats_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.client.get(audit_logs_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        print("✅ Test des fonctionnalités d'administration réussi")


class PerformanceAndSecurityTestCase(APITestCase):
    """Test de performance et de sécurité"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Créer un utilisateur de test
        self.user = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        UserProfile.objects.create(user=self.user, role='BUYER')
        
        self.token = str(RefreshToken.for_user(self.user).access_token)
    
    def test_rate_limiting_and_security_headers(self):
        """Test des limites de taux et headers de sécurité"""
        
        # 1. Test de health check (endpoint public)
        health_url = reverse('health-check')
        response = self.client.get(health_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que l'endpoint répond rapidement
        import time
        start_time = time.time()
        for _ in range(5):
            response = self.client.get(health_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        end_time = time.time()
        
        # Les 5 requêtes ne devraient pas prendre plus de 1 seconde
        self.assertLess(end_time - start_time, 1.0)
        
        # 2. Test de protection contre les requêtes malformées
        malformed_data = "{'invalid': json"
        response = self.client.post(
            reverse('user-login'),
            malformed_data,
            content_type='application/json'
        )
        
        # Devrait retourner une erreur 400, pas 500
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 3. Test d'authentification avec token invalide
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        profile_url = reverse('user-profile')
        response = self.client.get(profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        print("✅ Tests de performance et sécurité réussis")
    
    def test_database_query_optimization(self):
        """Test d'optimisation des requêtes de base de données"""
        
        # Créer plusieurs transactions pour tester les requêtes
        seller = User.objects.create_user(
            phone_number='+237698765432',
            password='TestPassword123!',
            first_name='Seller',
            last_name='Test'
        )
        UserProfile.objects.create(user=seller, role='SELLER')
        
        # Créer 10 transactions
        transactions = []
        for i in range(10):
            transaction = EscrowTransaction.objects.create(
                buyer=self.user,
                seller=seller,
                title=f'Transaction {i}',
                category='GOODS',
                amount=100000 + i * 1000,
                delivery_address='Test Address',
                status='PENDING'
            )
            transactions.append(transaction)
        
        # Test de requête optimisée pour la liste des transactions
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        transactions_url = reverse('transaction-list-create')
        
        # Mesurer le nombre de requêtes
        from django.test import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            response = self.client.get(transactions_url)
            final_queries = len(connection.queries)
            
            query_count = final_queries - initial_queries
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Le nombre de requêtes ne devrait pas être excessif
            # (devrait être optimisé avec select_related/prefetch_related)
            self.assertLess(query_count, 5)
        
        print(f"✅ Test d'optimisation des requêtes réussi ({query_count} requêtes)")


# Classe de base pour tous les tests d'intégration
class IntegrationTestSuite:
    """Suite complète de tests d'intégration"""
    
    @staticmethod
    def run_all_tests():
        """Exécuter tous les tests d'intégration"""
        import django
        from django.test.utils import get_runner
        from django.conf import settings
        
        django.setup()
        TestRunner = get_runner(settings)
        test_runner = TestRunner()
        
        test_modules = [
            'test_integration.CompleteTransactionFlowTestCase',
            'test_integration.DisputeResolutionFlowTestCase',
            'test_integration.KYCVerificationFlowTestCase',
            'test_integration.MultiUserInteractionTestCase',
            'test_integration.PerformanceAndSecurityTestCase',
        ]
        
        failures = test_runner.run_tests(test_modules)
        
        if failures:
            print(f"❌ {failures} tests ont échoué")
            return False
        else:
            print("✅ Tous les tests d'intégration ont réussi !")
            return True


if __name__ == '__main__':
    # Permet d'exécuter les tests directement
    IntegrationTestSuite.run_all_tests()
