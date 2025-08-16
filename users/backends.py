"""
Backends d'authentification personnalisés pour Kimi Escrow
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailBackend(ModelBackend):
    """
    Backend d'authentification personnalisé qui utilise l'email comme identifiant
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            # Essayer de trouver l'utilisateur par email
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            # Essayer par numéro de téléphone (pour la compatibilité)
            try:
                user = UserModel.objects.get(phone_number=username)
            except UserModel.DoesNotExist:
                return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
    
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
