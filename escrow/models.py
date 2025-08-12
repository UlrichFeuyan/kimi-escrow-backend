from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import TimeStampedModel
from core.utils import generate_transaction_id, calculate_commission, get_auto_release_date, get_dispute_timeout_date

User = get_user_model()


class EscrowTransaction(TimeStampedModel):
    """Modèle principal pour les transactions escrow"""
    STATUS_CHOICES = [
        ('PENDING_FUNDS', 'En attente de fonds'),
        ('FUNDS_HELD', 'Fonds en séquestre'),
        ('DELIVERED', 'Livré'),
        ('RELEASED', 'Fonds libérés'),
        ('DISPUTE', 'En litige'),
        ('REFUNDED', 'Remboursé'),
        ('CANCELLED', 'Annulé'),
    ]
    
    CATEGORY_CHOICES = [
        ('GOODS', 'Biens matériels'),
        ('SERVICES', 'Services'),
        ('DIGITAL', 'Produits numériques'),
        ('REAL_ESTATE', 'Immobilier'),
        ('VEHICLES', 'Véhicules'),
        ('OTHER', 'Autre'),
    ]
    
    # Identifiants
    transaction_id = models.CharField(max_length=20, unique=True, default=generate_transaction_id)
    
    # Participants
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='purchases')
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales')
    
    # Détails de la transaction
    title = models.CharField(max_length=200, help_text="Titre de la transaction")
    description = models.TextField(help_text="Description détaillée")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GOODS')
    
    # Montants (en XAF)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('1000.00'))])
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Statut et dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_FUNDS')
    
    # Dates importantes
    payment_deadline = models.DateTimeField(help_text="Date limite de paiement")
    delivery_deadline = models.DateTimeField(help_text="Date limite de livraison")
    auto_release_date = models.DateTimeField(null=True, blank=True)
    dispute_deadline = models.DateTimeField(null=True, blank=True)
    
    # Dates de changement de statut
    funds_received_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Configurations
    auto_release_enabled = models.BooleanField(default=True)
    auto_release_days = models.PositiveIntegerField(default=14)
    require_delivery_confirmation = models.BooleanField(default=True)
    
    # Informations de livraison
    delivery_address = models.TextField(blank=True)
    delivery_method = models.CharField(max_length=100, blank=True)
    tracking_info = models.CharField(max_length=200, blank=True)
    
    # Métadonnées
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Transaction Escrow"
        verbose_name_plural = "Transactions Escrow"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['auto_release_date']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.commission:
            self.commission = calculate_commission(self.amount)
        
        if not self.total_amount:
            self.total_amount = self.amount + self.commission
        
        if not self.auto_release_date and self.auto_release_enabled:
            if self.status == 'DELIVERED':
                self.auto_release_date = timezone.now() + timezone.timedelta(days=self.auto_release_days)
        
        if not self.dispute_deadline and self.status == 'DELIVERED':
            self.dispute_deadline = get_dispute_timeout_date()
        
        super().save(*args, **kwargs)
    
    def can_be_cancelled(self, user):
        """Vérifier si la transaction peut être annulée"""
        if self.status not in ['PENDING_FUNDS', 'FUNDS_HELD']:
            return False
        
        if user == self.buyer and self.status == 'PENDING_FUNDS':
            return True
        
        if user == self.seller and self.status in ['PENDING_FUNDS', 'FUNDS_HELD']:
            return True
        
        return False
    
    def can_mark_delivered(self, user):
        """Vérifier si l'utilisateur peut marquer comme livré"""
        return (user == self.seller and 
                self.status == 'FUNDS_HELD' and 
                timezone.now() <= self.delivery_deadline)
    
    def can_confirm_delivery(self, user):
        """Vérifier si l'utilisateur peut confirmer la livraison"""
        return (user == self.buyer and self.status == 'DELIVERED')
    
    def can_create_dispute(self, user):
        """Vérifier si l'utilisateur peut créer un litige"""
        if self.status not in ['DELIVERED', 'FUNDS_HELD']:
            return False
        
        if user not in [self.buyer, self.seller]:
            return False
        
        if self.dispute_deadline and timezone.now() > self.dispute_deadline:
            return False
        
        return True
    
    def get_participant_role(self, user):
        """Obtenir le rôle de l'utilisateur dans la transaction"""
        if user == self.buyer:
            return 'buyer'
        elif user == self.seller:
            return 'seller'
        return None
    
    def get_other_participant(self, user):
        """Obtenir l'autre participant de la transaction"""
        if user == self.buyer:
            return self.seller
        elif user == self.seller:
            return self.buyer
        return None
    
    def is_overdue(self):
        """Vérifier si la transaction est en retard"""
        now = timezone.now()
        
        if self.status == 'PENDING_FUNDS' and now > self.payment_deadline:
            return True
        
        if self.status == 'FUNDS_HELD' and now > self.delivery_deadline:
            return True
        
        return False
    
    def should_auto_release(self):
        """Vérifier si les fonds doivent être libérés automatiquement"""
        return (self.auto_release_enabled and 
                self.auto_release_date and 
                timezone.now() >= self.auto_release_date and
                self.status == 'DELIVERED')


class Milestone(TimeStampedModel):
    """Jalons pour les transactions complexes"""
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('IN_PROGRESS', 'En cours'),
        ('COMPLETED', 'Terminé'),
        ('APPROVED', 'Approuvé'),
        ('REJECTED', 'Rejeté'),
    ]
    
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    order = models.PositiveIntegerField(default=1)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_milestones')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_milestones')
    
    completion_notes = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Jalon"
        verbose_name_plural = "Jalons"
        ordering = ['transaction', 'order']
        unique_together = ['transaction', 'order']
    
    def __str__(self):
        return f"{self.transaction.transaction_id} - Milestone {self.order}: {self.title}"


class Proof(TimeStampedModel):
    """Preuves de livraison et documents associés"""
    PROOF_TYPE_CHOICES = [
        ('DELIVERY_PHOTO', 'Photo de livraison'),
        ('RECEIPT', 'Reçu'),
        ('SIGNATURE', 'Signature'),
        ('TRACKING', 'Numéro de suivi'),
        ('INVOICE', 'Facture'),
        ('WARRANTY', 'Garantie'),
        ('OTHER', 'Autre'),
    ]
    
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='proofs')
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, null=True, blank=True, related_name='proofs')
    
    proof_type = models.CharField(max_length=20, choices=PROOF_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    file = models.FileField(upload_to='proofs/%Y/%m/%d/', null=True, blank=True)
    text_content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_proofs')
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_proofs')
    verification_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Preuve"
        verbose_name_plural = "Preuves"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction.transaction_id} - {self.get_proof_type_display()}: {self.title}"


class TransactionMessage(TimeStampedModel):
    """Messages entre les participants d'une transaction"""
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    
    message = models.TextField()
    is_system_message = models.BooleanField(default=False)
    
    attachment = models.FileField(upload_to='messages/%Y/%m/%d/', null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Message de Transaction"
        verbose_name_plural = "Messages de Transaction"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.transaction.transaction_id} - Message de {self.sender.get_full_name()}"


class TransactionRating(TimeStampedModel):
    """Évaluations après completion des transactions"""
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='ratings')
    rater = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings')
    rated_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_ratings')
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    
    communication_rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    delivery_rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    quality_rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    would_recommend = models.BooleanField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Évaluation de Transaction"
        verbose_name_plural = "Évaluations de Transaction"
        unique_together = ['transaction', 'rater', 'rated_user']
    
    def __str__(self):
        return f"{self.transaction.transaction_id} - {self.rater.get_full_name()} évalue {self.rated_user.get_full_name()}: {self.rating}★"