import json
import tempfile
from io import BytesIO
from PIL import Image
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock
from .models import UserProfile, KYCDocument
from .serializers import UserRegistrationSerializer

User = get_user_model()


class AuthenticationTestCase(APITestCase):
    """Tests pour les endpoints d'authentification"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.logout_url = reverse('user-logout')
        
        # Données de test
        self.user_data = {
            'phone_number': '+237612345678',
            'password': 'TestPassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'BUYER'
        }
        
        # Créer un utilisateur de test
        self.test_user = User.objects.create_user(
            phone_number='+237698765432',
            password='TestPassword123!',
            first_name='Jane',
            last_name='Smith'
        )
        self.test_profile = UserProfile.objects.create(
            user=self.test_user,
            role='SELLER'
        )
    
    def test_user_registration_success(self):
        """Test d'inscription utilisateur réussie"""
        with patch('users.services.SmileIDService.send_sms') as mock_sms:
            mock_sms.return_value = True
            
            response = self.client.post(self.register_url, self.user_data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['success'])
            self.assertIn('tokens', response.data['data'])
            self.assertIn('access', response.data['data']['tokens'])
            self.assertIn('refresh', response.data['data']['tokens'])
            
            # Vérifier que l'utilisateur a été créé
            user = User.objects.get(phone_number=self.user_data['phone_number'])
            self.assertEqual(user.first_name, self.user_data['first_name'])
            self.assertEqual(user.last_name, self.user_data['last_name'])
            
            # Vérifier que le profil a été créé
            self.assertTrue(hasattr(user, 'profile'))
            self.assertEqual(user.profile.role, self.user_data['role'])
    
    def test_user_registration_duplicate_phone(self):
        """Test d'inscription avec numéro déjà utilisé"""
        duplicate_data = self.user_data.copy()
        duplicate_data['phone_number'] = self.test_user.phone_number
        
        response = self.client.post(self.register_url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('phone_number', response.data['errors'])
    
    def test_user_login_success(self):
        """Test de connexion réussie"""
        login_data = {
            'phone_number': self.test_user.phone_number,
            'password': 'TestPassword123!'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data['data'])
        self.assertIn('user', response.data['data'])
        self.assertEqual(response.data['data']['user']['phone_number'], self.test_user.phone_number)
    
    def test_user_login_invalid_credentials(self):
        """Test de connexion avec identifiants invalides"""
        invalid_data = {
            'phone_number': self.test_user.phone_number,
            'password': 'wrong_password'
        }
        
        response = self.client.post(self.login_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
    
    def test_user_logout(self):
        """Test de déconnexion"""
        # Obtenir un token
        refresh = RefreshToken.for_user(self.test_user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        logout_data = {'refresh_token': refresh_token}
        response = self.client.post(self.logout_url, logout_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class UserProfileTestCase(APITestCase):
    """Tests pour les endpoints de profil utilisateur"""
    
    def setUp(self):
        self.client = APIClient()
        self.profile_url = reverse('user-profile')
        self.change_password_url = reverse('change-password')
        
        # Créer un utilisateur de test
        self.test_user = User.objects.create_user(
            phone_number='+237612345678',
            password='TestPassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.test_profile = UserProfile.objects.create(
            user=self.test_user,
            role='BUYER'
        )
        
        # Authentifier l'utilisateur
        refresh = RefreshToken.for_user(self.test_user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_get_user_profile(self):
        """Test de récupération du profil utilisateur"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['phone_number'], self.test_user.phone_number)
        self.assertEqual(response.data['data']['role'], self.test_profile.role)
    
    def test_update_user_profile(self):
        """Test de mise à jour du profil utilisateur"""
        update_data = {
            'first_name': 'Johnny',
            'last_name': 'Smith',
            'location': 'Douala, Cameroun'
        }
        
        response = self.client.patch(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Vérifier que les données ont été mises à jour
        self.test_user.refresh_from_db()
        self.test_profile.refresh_from_db()
        self.assertEqual(self.test_user.first_name, 'Johnny')
        self.assertEqual(self.test_user.last_name, 'Smith')
        self.assertEqual(self.test_profile.location, 'Douala, Cameroun')
    
    def test_change_password_success(self):
        """Test de changement de mot de passe réussi"""
        password_data = {
            'old_password': 'TestPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'NewPassword456!'
        }
        
        response = self.client.post(self.change_password_url, password_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Vérifier que le mot de passe a été changé
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.check_password('NewPassword456!'))
