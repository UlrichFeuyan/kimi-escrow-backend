from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from core.models import TimeStampedModel
from core.utils import generate_secure_token
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé avec rôles et KYC
    """
    ROLE_CHOICES = [
        ('BUYER', 'Acheteur'),
        ('SELLER', 'Vendeur'),
        ('ARBITRE', 'Arbitre'),
        ('ADMIN', 'Administrateur'),
    ]
    
    KYC_STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('SUBMITTED', 'Soumis'),
        ('UNDER_REVIEW', 'En cours de vérification'),
        ('VERIFIED', 'Vérifié'),
        ('REJECTED', 'Rejeté'),
        ('EXPIRED', 'Expiré'),
    ]
    
    # Utiliser phone_number comme identifiant unique au lieu d'username
    username = None
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    
    # Informations personnelles
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Rôle et statut
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='BUYER')
    is_phone_verified = models.BooleanField(default=False)
    phone_verification_token = models.CharField(max_length=6, blank=True)
    phone_verification_expires_at = models.DateTimeField(null=True, blank=True)
    
    # KYC Information
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='PENDING')
    kyc_submitted_at = models.DateTimeField(null=True, blank=True)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    kyc_rejection_reason = models.TextField(blank=True)
    
    # Informations d'identification
    id_card_number = models.CharField(max_length=50, blank=True)
    id_card_type = models.CharField(max_length=20, choices=[
        ('CNI', 'Carte Nationale d\'Identité'),
        ('PASSPORT', 'Passeport'),
        ('DRIVER_LICENSE', 'Permis de Conduire'),
    ], blank=True)
    
    # Adresse
    address_street = models.CharField(max_length=255, blank=True)
    address_city = models.CharField(max_length=100, blank=True)
    address_region = models.CharField(max_length=100, blank=True)
    address_country = models.CharField(max_length=100, default='Cameroun')
    
    # Préférences
    preferred_language = models.CharField(max_length=10, choices=[
        ('fr', 'Français'),
        ('en', 'English'),
    ], default='fr')
    
    # MFA pour les admins et arbitres
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['role']),
            models.Index(fields=['kyc_status']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def can_create_escrow(self):
        """Vérifier si l'utilisateur peut créer une transaction escrow"""
        return (self.role in ['BUYER', 'SELLER'] and 
                self.kyc_status == 'VERIFIED' and 
                self.is_phone_verified)
    
    def can_arbitrate(self):
        """Vérifier si l'utilisateur peut arbitrer"""
        return self.role == 'ARBITRE' and self.kyc_status == 'VERIFIED'
    
    def generate_phone_verification_token(self):
        """Générer un token de vérification SMS"""
        import random
        from django.utils import timezone
        from datetime import timedelta
        
        self.phone_verification_token = str(random.randint(100000, 999999))
        self.phone_verification_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['phone_verification_token', 'phone_verification_expires_at'])
        return self.phone_verification_token


class KYCDocument(TimeStampedModel):
    """
    Documents KYC uploadés par les utilisateurs
    """
    DOCUMENT_TYPES = [
        ('ID_FRONT', 'Pièce d\'identité (recto)'),
        ('ID_BACK', 'Pièce d\'identité (verso)'),
        ('SELFIE', 'Photo selfie'),
        ('PROOF_OF_ADDRESS', 'Justificatif de domicile'),
        ('SIGNATURE', 'Signature'),
    ]
    
    STATUS_CHOICES = [
        ('UPLOADED', 'Uploadé'),
        ('PROCESSING', 'En cours de traitement'),
        ('VERIFIED', 'Vérifié'),
        ('REJECTED', 'Rejeté'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='kyc_documents/%Y/%m/%d/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADED')
    
    # Résultats de la vérification Smile ID
    smile_id_job_id = models.CharField(max_length=100, blank=True)
    smile_id_result = models.JSONField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Métadonnées du fichier
    file_size = models.PositiveIntegerField(null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)  # SHA-256
    
    class Meta:
        unique_together = ['user', 'document_type']
        verbose_name = 'Document KYC'
        verbose_name_plural = 'Documents KYC'
    
    def __str__(self):
        return f"{self.user} - {self.get_document_type_display()}"


class UserProfile(TimeStampedModel):
    """
    Profil étendu de l'utilisateur avec préférences et statistiques
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Avatar
    avatar = models.ImageField(upload_to='avatars/%Y/%m/%d/', null=True, blank=True)
    
    # Informations professionnelles
    occupation = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    
    # Préférences de notification
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    # Préférences d'escrow
    default_auto_release_days = models.PositiveIntegerField(default=14)
    require_confirmation_for_release = models.BooleanField(default=True)
    
    # Statistiques
    total_transactions = models.PositiveIntegerField(default=0)
    successful_transactions = models.PositiveIntegerField(default=0)
    total_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    
    # Vérifications supplémentaires
    email_verified = models.BooleanField(default=False)
    bank_account_verified = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Profil Utilisateur'
        verbose_name_plural = 'Profils Utilisateurs'
    
    def __str__(self):
        return f"Profil de {self.user.get_full_name()}"
    
    def update_statistics(self):
        """Mettre à jour les statistiques de l'utilisateur"""
        from escrow.models import EscrowTransaction
        
        transactions = EscrowTransaction.objects.filter(
            models.Q(buyer=self.user) | models.Q(seller=self.user)
        )
        
        self.total_transactions = transactions.count()
        self.successful_transactions = transactions.filter(status='RELEASED').count()
        self.total_volume = sum(t.amount for t in transactions.filter(status='RELEASED'))
        self.save(update_fields=['total_transactions', 'successful_transactions', 'total_volume'])


class UserSession(models.Model):
    """
    Sessions utilisateur pour le suivi des connexions
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    device_info = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.device_info}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class LoginAttempt(models.Model):
    """
    Tentatives de connexion pour la sécurité
    """
    phone_number = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['phone_number', 'attempted_at']),
            models.Index(fields=['ip_address', 'attempted_at']),
        ]
    
    def __str__(self):
        status = "Succès" if self.success else f"Échec ({self.failure_reason})"
        return f"{self.phone_number} - {status} - {self.attempted_at}"