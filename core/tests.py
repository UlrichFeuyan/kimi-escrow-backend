import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock
from .models import GlobalSettings, AuditLog
from users.models import UserProfile

User = get_user_model()


class HealthCheckTestCase(APITestCase):
    """Tests pour l'endpoint de vérification de santé"""
    
    def setUp(self):
        self.client = APIClient()
        self.health_url = reverse('health-check')
    
    def test_health_check_success(self):
        """Test de vérification de santé réussie"""
        response = self.client.get(self.health_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('version', response.data)
        self.assertIn('database', response.data)
        self.assertIn('cache', response.data)
        
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['database']['status'], 'connected')
    
    @patch('django.db.connection.ensure_connection')
    def test_health_check_database_error(self, mock_connection):
        """Test de vérification de santé avec erreur de base de données"""
        mock_connection.side_effect = Exception("Database connection failed")
        
        response = self.client.get(self.health_url)
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data['status'], 'unhealthy')
        self.assertEqual(response.data['database']['status'], 'error')
    
    @patch('django.core.cache.cache.get')
    def test_health_check_cache_error(self, mock_cache):
        """Test de vérification de santé avec erreur de cache"""
        mock_cache.side_effect = Exception("Cache connection failed")
        
        response = self.client.get(self.health_url)
        
        # Le système devrait toujours fonctionner même si le cache échoue
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cache']['status'], 'error')


class GlobalSettingsTestCase(APITestCase):
    """Tests pour les paramètres globaux"""
    
    def setUp(self):
        self.client = APIClient()
        self.settings_url = reverse('global-settings')
        
        # Créer un utilisateur admin
        self.admin = User.objects.create_user(
            phone_number='+237600000000',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User',
            is_staff=True
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin,
            role='ADMIN'
        )
        
        # Créer un utilisateur normal
        self.user = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='John',
            last_name='User'
        )
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            role='BUYER'
        )
        
        # Créer quelques paramètres globaux
        GlobalSettings.objects.create(
            key='MAX_TRANSACTION_AMOUNT',
            value='1000000',
            description='Montant maximum pour une transaction'
        )
        GlobalSettings.objects.create(
            key='KYC_REQUIRED_AMOUNT',
            value='50000',
            description='Montant à partir duquel le KYC est requis'
        )
        GlobalSettings.objects.create(
            key='PLATFORM_FEE_PERCENTAGE',
            value='2.5',
            description='Pourcentage de frais de plateforme'
        )
    
    def test_get_global_settings_admin(self):
        """Test de récupération des paramètres globaux (admin)"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        response = self.client.get(self.settings_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        settings = response.data['data']['results']
        self.assertEqual(len(settings), 3)
        
        # Vérifier que les paramètres sont présents
        setting_keys = [setting['key'] for setting in settings]
        self.assertIn('MAX_TRANSACTION_AMOUNT', setting_keys)
        self.assertIn('KYC_REQUIRED_AMOUNT', setting_keys)
        self.assertIn('PLATFORM_FEE_PERCENTAGE', setting_keys)
    
    def test_get_global_settings_user(self):
        """Test de récupération des paramètres globaux (utilisateur normal)"""
        # Authentifier l'utilisateur normal
        refresh = RefreshToken.for_user(self.user)
        user_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')
        
        response = self.client.get(self.settings_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Les utilisateurs normaux peuvent voir les paramètres publics
        settings = response.data['data']['results']
        self.assertGreater(len(settings), 0)
    
    def test_get_global_settings_unauthenticated(self):
        """Test d'accès non authentifié aux paramètres globaux"""
        response = self.client.get(self.settings_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_global_settings_filtering(self):
        """Test de filtrage des paramètres globaux"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        # Filtrer par clé
        response = self.client.get(self.settings_url, {'key': 'MAX_TRANSACTION_AMOUNT'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        settings = response.data['data']['results']
        self.assertEqual(len(settings), 1)
        self.assertEqual(settings[0]['key'], 'MAX_TRANSACTION_AMOUNT')


class AuditLogTestCase(APITestCase):
    """Tests pour les logs d'audit"""
    
    def setUp(self):
        self.client = APIClient()
        self.audit_url = reverse('audit-logs')
        
        # Créer un utilisateur admin
        self.admin = User.objects.create_user(
            phone_number='+237600000000',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User',
            is_staff=True
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin,
            role='ADMIN'
        )
        
        # Créer des utilisateurs normaux
        self.user1 = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='John',
            last_name='User'
        )
        UserProfile.objects.create(user=self.user1, role='BUYER')
        
        self.user2 = User.objects.create_user(
            phone_number='+237698765432',
            password='TestPassword123!',
            first_name='Jane',
            last_name='User'
        )
        UserProfile.objects.create(user=self.user2, role='SELLER')
        
        # Créer quelques logs d'audit
        AuditLog.objects.create(
            user=self.user1,
            action='USER_LOGIN',
            resource_type='USER',
            resource_id=self.user1.id,
            details={'ip_address': '192.168.1.1', 'user_agent': 'Mozilla/5.0'}
        )
        
        AuditLog.objects.create(
            user=self.user1,
            action='TRANSACTION_CREATED',
            resource_type='TRANSACTION',
            resource_id=1,
            details={'amount': 100000, 'seller_id': self.user2.id}
        )
        
        AuditLog.objects.create(
            user=self.admin,
            action='KYC_APPROVED',
            resource_type='USER',
            resource_id=self.user1.id,
            details={'admin_notes': 'Documents vérifiés'}
        )
    
    def test_get_audit_logs_admin(self):
        """Test de récupération des logs d'audit (admin)"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        response = self.client.get(self.audit_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 3)
        
        # Vérifier que les logs sont ordonnés par date (plus récent en premier)
        timestamps = [log['timestamp'] for log in logs]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_get_audit_logs_non_admin(self):
        """Test d'accès refusé pour non-admin"""
        # Authentifier un utilisateur normal
        refresh = RefreshToken.for_user(self.user1)
        user_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')
        
        response = self.client.get(self.audit_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_audit_logs_filtering_by_user(self):
        """Test de filtrage des logs par utilisateur"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        # Filtrer par utilisateur
        response = self.client.get(self.audit_url, {'user_id': self.user1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 2)  # user1 a 2 actions
        
        for log in logs:
            self.assertEqual(log['user']['id'], self.user1.id)
    
    def test_audit_logs_filtering_by_action(self):
        """Test de filtrage des logs par action"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        # Filtrer par action
        response = self.client.get(self.audit_url, {'action': 'USER_LOGIN'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['action'], 'USER_LOGIN')
    
    def test_audit_logs_filtering_by_resource_type(self):
        """Test de filtrage des logs par type de ressource"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        # Filtrer par type de ressource
        response = self.client.get(self.audit_url, {'resource_type': 'USER'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 2)  # 2 actions sur des USER
        
        for log in logs:
            self.assertEqual(log['resource_type'], 'USER')
    
    def test_audit_logs_date_range_filtering(self):
        """Test de filtrage des logs par plage de dates"""
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        # Utiliser une date d'aujourd'hui
        from datetime import date
        today = date.today().isoformat()
        
        response = self.client.get(self.audit_url, {
            'date_from': today,
            'date_to': today
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Tous les logs créés aujourd'hui devraient être retournés
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 3)
    
    def test_audit_logs_pagination(self):
        """Test de pagination des logs d'audit"""
        # Créer plus de logs pour tester la pagination
        for i in range(15):
            AuditLog.objects.create(
                user=self.user1,
                action=f'TEST_ACTION_{i}',
                resource_type='TEST',
                resource_id=i,
                details={'test': f'data_{i}'}
            )
        
        # Authentifier l'admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        # Tester la première page
        response = self.client.get(self.audit_url, {'page': 1, 'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 10)
        self.assertIsNotNone(response.data['data']['next'])
        
        # Tester la deuxième page
        response = self.client.get(self.audit_url, {'page': 2, 'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logs = response.data['data']['results']
        self.assertEqual(len(logs), 8)  # 18 total - 10 première page = 8


class CoreMiddlewareTestCase(TestCase):
    """Tests pour les middlewares core"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Créer un utilisateur de test
        self.user = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='John',
            last_name='User'
        )
        UserProfile.objects.create(user=self.user, role='BUYER')
    
    def test_audit_middleware_logs_user_actions(self):
        """Test que le middleware d'audit enregistre les actions utilisateur"""
        # Authentifier l'utilisateur
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Compter les logs avant l'action
        initial_count = AuditLog.objects.count()
        
        # Faire une action qui devrait être loggée
        profile_url = reverse('user-profile')
        response = self.client.get(profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier qu'un nouveau log a été créé
        final_count = AuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Vérifier le contenu du log
        latest_log = AuditLog.objects.latest('timestamp')
        self.assertEqual(latest_log.user, self.user)
        self.assertEqual(latest_log.action, 'GET_USER_PROFILE')
    
    def test_audit_middleware_anonymous_user(self):
        """Test que le middleware ne logue pas les actions des utilisateurs anonymes"""
        initial_count = AuditLog.objects.count()
        
        # Faire une action sans authentification
        health_url = reverse('health-check')
        response = self.client.get(health_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier qu'aucun log n'a été créé
        final_count = AuditLog.objects.count()
        self.assertEqual(final_count, initial_count)


class CoreUtilsTestCase(TestCase):
    """Tests pour les utilitaires core"""
    
    def test_generate_reference_number(self):
        """Test de génération de numéro de référence"""
        from .utils import generate_reference_number
        
        # Tester la génération avec préfixe
        ref1 = generate_reference_number('TXN')
        self.assertTrue(ref1.startswith('TXN-'))
        self.assertEqual(len(ref1), 16)  # TXN- + 12 caractères
        
        # Tester l'unicité
        ref2 = generate_reference_number('TXN')
        self.assertNotEqual(ref1, ref2)
        
        # Tester sans préfixe
        ref3 = generate_reference_number()
        self.assertEqual(len(ref3), 12)
    
    def test_phone_number_validation(self):
        """Test de validation des numéros de téléphone"""
        from .utils import validate_phone_number
        
        # Numéros valides
        valid_numbers = [
            '+237612345678',
            '+237698765432',
            '+237655555555'
        ]
        
        for number in valid_numbers:
            self.assertTrue(validate_phone_number(number))
        
        # Numéros invalides
        invalid_numbers = [
            '612345678',  # Pas de code pays
            '+336123456789',  # Mauvais code pays
            '+237612',  # Trop court
            '+2376123456789',  # Trop long
            'not_a_number'  # Pas un numéro
        ]
        
        for number in invalid_numbers:
            self.assertFalse(validate_phone_number(number))
    
    def test_amount_formatting(self):
        """Test de formatage des montants"""
        from .utils import format_amount
        
        # Test avec différents montants
        self.assertEqual(format_amount(1000), '1 000 FCFA')
        self.assertEqual(format_amount(1234567), '1 234 567 FCFA')
        self.assertEqual(format_amount(0), '0 FCFA')
        
        # Test avec décimales
        self.assertEqual(format_amount(1000.50), '1 000,50 FCFA')
    
    def test_hash_verification(self):
        """Test de hachage et vérification"""
        from .utils import generate_hash, verify_hash
        
        data = "test_data_for_hashing"
        secret = "secret_key"
        
        # Générer un hash
        hash_value = generate_hash(data, secret)
        self.assertIsInstance(hash_value, str)
        self.assertGreater(len(hash_value), 0)
        
        # Vérifier le hash
        self.assertTrue(verify_hash(data, hash_value, secret))
        
        # Vérifier avec des données incorrectes
        self.assertFalse(verify_hash("wrong_data", hash_value, secret))
        self.assertFalse(verify_hash(data, hash_value, "wrong_secret"))


class CorePermissionsTestCase(APITestCase):
    """Tests pour les permissions core"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Créer des utilisateurs avec différents rôles
        self.admin = User.objects.create_user(
            phone_number='+237600000000',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User',
            is_staff=True
        )
        UserProfile.objects.create(user=self.admin, role='ADMIN')
        
        self.buyer = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='John',
            last_name='Buyer'
        )
        UserProfile.objects.create(user=self.buyer, role='BUYER')
        
        self.seller = User.objects.create_user(
            phone_number='+237698765432',
            password='TestPassword123!',
            first_name='Jane',
            last_name='Seller'
        )
        UserProfile.objects.create(user=self.seller, role='SELLER')
        
        self.arbitre = User.objects.create_user(
            phone_number='+237655555555',
            password='TestPassword123!',
            first_name='John',
            last_name='Arbitre'
        )
        UserProfile.objects.create(user=self.arbitre, role='ARBITRE')
    
    def test_admin_only_endpoints(self):
        """Test que seuls les admins peuvent accéder aux endpoints admin"""
        admin_urls = [
            reverse('audit-logs'),
        ]
        
        # Tester avec admin
        refresh = RefreshToken.for_user(self.admin)
        admin_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        for url in admin_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 201])  # Success
        
        # Tester avec utilisateur normal
        refresh = RefreshToken.for_user(self.buyer)
        buyer_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {buyer_token}')
        
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_authenticated_required_endpoints(self):
        """Test que l'authentification est requise pour certains endpoints"""
        auth_required_urls = [
            reverse('global-settings'),
        ]
        
        # Tester sans authentification
        self.client.credentials()
        
        for url in auth_required_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)  # Unauthorized
        
        # Tester avec authentification
        refresh = RefreshToken.for_user(self.buyer)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        for url in auth_required_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 201])  # Success
    
    def test_public_endpoints(self):
        """Test que les endpoints publics sont accessibles sans authentification"""
        public_urls = [
            reverse('health-check'),
        ]
        
        # Tester sans authentification
        self.client.credentials()
        
        for url in public_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 201])  # Success
