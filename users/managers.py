from django.contrib.auth.models import BaseUserManager
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """
    Gestionnaire personnalisé pour le modèle CustomUser
    """
    
    def create_user(self, phone_number, password=None, **extra_fields):
        """
        Créer et sauvegarder un utilisateur avec le numéro de téléphone donné et le mot de passe.
        """
        if not phone_number:
            raise ValueError('Le numéro de téléphone doit être défini')
        
        # Normaliser le numéro de téléphone
        from core.utils import sanitize_phone_number
        phone_number = sanitize_phone_number(phone_number)
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        # Le profil utilisateur sera créé automatiquement par les signals
        pass
        
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        """
        Créer et sauvegarder un superutilisateur avec le numéro de téléphone donné et le mot de passe.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('kyc_status', 'VERIFIED')
        extra_fields.setdefault('is_phone_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')
        
        return self.create_user(phone_number, password, **extra_fields)
    
    def get_by_natural_key(self, username):
        """
        Obtenir un utilisateur par son identifiant naturel (phone_number)
        """
        return self.get(phone_number=username)
    
    def verified_users(self):
        """
        Retourner les utilisateurs avec KYC vérifié
        """
        return self.filter(kyc_status='VERIFIED', is_phone_verified=True)
    
    def buyers(self):
        """
        Retourner les acheteurs
        """
        return self.filter(role='BUYER')
    
    def sellers(self):
        """
        Retourner les vendeurs
        """
        return self.filter(role='SELLER')
    
    def arbitres(self):
        """
        Retourner les arbitres
        """
        return self.filter(role='ARBITRE')
    
    def active_this_month(self):
        """
        Retourner les utilisateurs actifs ce mois-ci
        """
        from datetime import timedelta
        one_month_ago = timezone.now() - timedelta(days=30)
        return self.filter(last_activity__gte=one_month_ago)
