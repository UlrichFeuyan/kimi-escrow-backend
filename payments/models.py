from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import TimeStampedModel
from core.utils import generate_payment_reference
from escrow.models import EscrowTransaction

User = get_user_model()


class PaymentMethod(TimeStampedModel):
    """
    Méthodes de paiement disponibles
    """
    PROVIDER_CHOICES = [
        ('MTN_MOMO', 'MTN Mobile Money'),
        ('ORANGE_MONEY', 'Orange Money'),
        ('BANK_TRANSFER', 'Virement bancaire'),
        ('ESCROW_BANK', 'Compte séquestre'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Actif'),
        ('INACTIVE', 'Inactif'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Configuration
    supports_collection = models.BooleanField(default=True)
    supports_disbursement = models.BooleanField(default=True)
    min_amount = models.DecimalField(max_digits=15, decimal_places=2, default=100)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2, default=1000000)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Métadonnées
    logo = models.ImageField(upload_to='payment_methods/', null=True, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Méthode de Paiement"
        verbose_name_plural = "Méthodes de Paiement"
    
    def __str__(self):
        return self.name
    
    def is_available(self):
        return self.status == 'ACTIVE'


class Payment(TimeStampedModel):
    """
    Paiements et transactions financières
    """
    TYPE_CHOICES = [
        ('COLLECTION', 'Collecte de fonds'),
        ('DISBURSEMENT', 'Décaissement'),
        ('REFUND', 'Remboursement'),
        ('FEE', 'Frais de service'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('PROCESSING', 'En cours de traitement'),
        ('SUCCESS', 'Réussi'),
        ('FAILED', 'Échoué'),
        ('CANCELLED', 'Annulé'),
        ('TIMEOUT', 'Expiré'),
    ]
    
    # Identifiants
    reference = models.CharField(max_length=50, unique=True, default=generate_payment_reference)
    external_reference = models.CharField(max_length=100, blank=True)
    
    # Relations
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments')
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    
    # Détails du paiement
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='XAF')
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Informations de contact
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    
    # Métadonnées
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Dates importantes
    expires_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Réponses API
    provider_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['transaction', 'payment_type']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.get_payment_type_display()} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = self.amount + self.fee
        super().save(*args, **kwargs)
    
    def is_pending(self):
        return self.status in ['PENDING', 'PROCESSING']
    
    def is_successful(self):
        return self.status == 'SUCCESS'
    
    def is_failed(self):
        return self.status in ['FAILED', 'CANCELLED', 'TIMEOUT']
    
    def can_be_cancelled(self):
        return self.status in ['PENDING', 'PROCESSING']
    
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at


class Webhook(TimeStampedModel):
    """
    Webhooks reçus des fournisseurs de paiement
    """
    SOURCE_CHOICES = [
        ('MTN_MOMO', 'MTN Mobile Money'),
        ('ORANGE_MONEY', 'Orange Money'),
        ('ESCROW_BANK', 'Banque Séquestre'),
    ]
    
    STATUS_CHOICES = [
        ('RECEIVED', 'Reçu'),
        ('PROCESSING', 'En cours de traitement'),
        ('PROCESSED', 'Traité'),
        ('FAILED', 'Échoué'),
        ('IGNORED', 'Ignoré'),
    ]
    
    # Identifiants
    webhook_id = models.CharField(max_length=100, unique=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    
    # Données
    event_type = models.CharField(max_length=50)
    raw_data = models.JSONField()
    parsed_data = models.JSONField(default=dict, blank=True)
    
    # Traitement
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    headers = models.JSONField(default=dict, blank=True)
    
    # Traitement
    processing_attempts = models.PositiveIntegerField(default=0)
    last_processing_attempt = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['webhook_id']),
            models.Index(fields=['source', 'event_type']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.source} - {self.event_type} ({self.status})"
    
    def mark_as_processed(self, payment=None):
        self.status = 'PROCESSED'
        self.processed_at = timezone.now()
        if payment:
            self.payment = payment
        self.save(update_fields=['status', 'processed_at', 'payment'])
    
    def mark_as_failed(self, error_message):
        self.status = 'FAILED'
        self.error_message = error_message
        self.last_processing_attempt = timezone.now()
        self.processing_attempts += 1
        self.save(update_fields=['status', 'error_message', 'last_processing_attempt', 'processing_attempts'])


class EscrowAccount(TimeStampedModel):
    """
    Comptes séquestres pour les transactions
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Actif'),
        ('FROZEN', 'Gelé'),
        ('CLOSED', 'Fermé'),
    ]
    
    # Identifiants
    account_number = models.CharField(max_length=50, unique=True)
    
    # Relations
    transaction = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name='escrow_account')
    
    # Solde
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    frozen_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Métadonnées bancaires
    bank_reference = models.CharField(max_length=100, blank=True)
    bank_response = models.JSONField(default=dict, blank=True)
    
    # Dates
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Compte Séquestre"
        verbose_name_plural = "Comptes Séquestres"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Compte {self.account_number} - {self.transaction.transaction_id}"
    
    def available_balance(self):
        return self.balance - self.frozen_amount
    
    def can_withdraw(self, amount):
        return self.available_balance() >= amount and self.status == 'ACTIVE'
    
    def freeze_amount(self, amount):
        if self.available_balance() >= amount:
            self.frozen_amount += amount
            self.save(update_fields=['frozen_amount'])
            return True
        return False
    
    def unfreeze_amount(self, amount):
        if self.frozen_amount >= amount:
            self.frozen_amount -= amount
            self.save(update_fields=['frozen_amount'])
            return True
        return False


class PaymentAttempt(TimeStampedModel):
    """
    Tentatives de paiement pour tracking
    """
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='attempts')
    
    # Détails de la tentative
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Payment.STATUS_CHOICES)
    
    # Réponse du fournisseur
    provider_reference = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    response_code = models.CharField(max_length=10, blank=True)
    response_message = models.TextField(blank=True)
    
    # Timing
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Tentative de Paiement"
        verbose_name_plural = "Tentatives de Paiement"
        ordering = ['-created_at']
        unique_together = ['payment', 'attempt_number']
    
    def __str__(self):
        return f"{self.payment.reference} - Tentative {self.attempt_number} ({self.status})"