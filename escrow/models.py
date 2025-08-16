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
    
    TRANSACTION_TYPE_CHOICES = [
        ('STANDARD', 'Transaction Standard'),
        ('FACE_TO_FACE', 'Transaction Face-à-Face'),
        ('MILESTONE', 'Transaction par Jalons'),
        ('INTERNATIONAL', 'Transaction Internationale'),
    ]
    
    CATEGORY_CHOICES = [
        ('GOODS', 'Biens matériels'),
        ('SERVICES', 'Services'),
        ('DIGITAL', 'Produits numériques'),
        ('REAL_ESTATE', 'Immobilier'),
        ('VEHICLES', 'Véhicules'),
        ('OTHER', 'Autre'),
    ]
    
    CURRENCY_CHOICES = [
        ('XAF', 'Franc CFA'),
        ('USD', 'Dollar US'),
        ('EUR', 'Euro'),
        ('GBP', 'Livre Sterling'),
    ]
    
    # Identifiants
    transaction_id = models.CharField(max_length=20, unique=True, default=generate_transaction_id)
    
    # Participants
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='purchases')
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales')
    
    # Type de transaction
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='STANDARD')
    
    # Détails de la transaction
    title = models.CharField(max_length=200, help_text="Titre de la transaction")
    description = models.TextField(help_text="Description détaillée")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GOODS')
    
    # Montants (en XAF par défaut)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('1000.00'))])
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Devise (pour transactions internationales)
    currency = models.CharField(max_length=3, default='XAF', choices=CURRENCY_CHOICES)
    
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
            models.Index(fields=['transaction_type']),
            models.Index(fields=['currency']),
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
    
    def is_face_to_face(self):
        """Vérifier si c'est une transaction face-à-face"""
        return self.transaction_type == 'FACE_TO_FACE'
    
    def is_milestone(self):
        """Vérifier si c'est une transaction par jalons"""
        return self.transaction_type == 'MILESTONE'
    
    def is_international(self):
        """Vérifier si c'est une transaction internationale"""
        return self.transaction_type == 'INTERNATIONAL'


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


class FaceToFaceDetails(TimeStampedModel):
    """Détails spécifiques aux transactions face-à-face"""
    transaction = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name='face_to_face_details')
    
    # Lieu de rencontre
    meeting_location = models.CharField(max_length=255, help_text="Adresse ou lieu de rencontre")
    meeting_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    meeting_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    meeting_address = models.TextField(blank=True)
    
    # Date et heure de rencontre
    meeting_date = models.DateTimeField(help_text="Date et heure de la rencontre")
    meeting_duration = models.PositiveIntegerField(default=60, help_text="Durée prévue en minutes")
    
    # Timer d'auto-validation
    auto_validation_hours = models.PositiveIntegerField(default=24, help_text="Heures avant auto-validation")
    auto_validation_deadline = models.DateTimeField(null=True, blank=True)
    
    # Preuves
    initial_proof = models.ForeignKey('Proof', on_delete=models.SET_NULL, null=True, blank=True, related_name='face_to_face_initial')
    final_proof = models.ForeignKey('Proof', on_delete=models.SET_NULL, null=True, blank=True, related_name='face_to_face_final')
    
    # Statut de la rencontre
    meeting_status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Planifiée'),
        ('IN_PROGRESS', 'En cours'),
        ('COMPLETED', 'Terminée'),
        ('CANCELLED', 'Annulée'),
        ('DISPUTED', 'En litige'),
    ], default='SCHEDULED')
    
    # Notes et métadonnées
    meeting_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Détails Face-à-Face"
        verbose_name_plural = "Détails Face-à-Face"
    
    def __str__(self):
        return f"Face-à-Face: {self.transaction.transaction_id} - {self.meeting_location}"
    
    def save(self, *args, **kwargs):
        if not self.auto_validation_deadline and self.meeting_date:
            from datetime import timedelta
            from django.utils.dateparse import parse_datetime
            from django.utils import timezone
            
            # S'assurer que meeting_date est un objet datetime
            if isinstance(self.meeting_date, str):
                self.meeting_date = parse_datetime(self.meeting_date)
                if self.meeting_date is None:
                    raise ValueError(f"Format de date invalide: {self.meeting_date}")
            
            # S'assurer que c'est aware si nécessaire
            if self.meeting_date and timezone.is_naive(self.meeting_date):
                self.meeting_date = timezone.make_aware(self.meeting_date)
                
            self.auto_validation_deadline = self.meeting_date + timedelta(hours=self.auto_validation_hours)
        super().save(*args, **kwargs)


class InternationalDetails(TimeStampedModel):
    """Détails spécifiques aux transactions internationales"""
    transaction = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name='international_details')
    
    # Devises
    buyer_currency = models.CharField(max_length=3, choices=[
        ('XAF', 'Franc CFA'),
        ('USD', 'Dollar US'),
        ('EUR', 'Euro'),
        ('GBP', 'Livre Sterling'),
    ])
    seller_currency = models.CharField(max_length=3, choices=[
        ('XAF', 'Franc CFA'),
        ('USD', 'Dollar US'),
        ('EUR', 'Euro'),
        ('GBP', 'Livre Sterling'),
    ])
    
    # Taux de change
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    exchange_rate_fixed = models.BooleanField(default=False, help_text="Taux fixe ou variable")
    exchange_rate_date = models.DateTimeField(null=True, blank=True)
    
    # Documents d'export/import
    invoice_number = models.CharField(max_length=100, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    bill_of_lading = models.CharField(max_length=100, blank=True)
    
    # Transporteur et suivi
    carrier_name = models.CharField(max_length=100, blank=True, choices=[
        ('DHL', 'DHL'),
        ('FEDEX', 'FedEx'),
        ('UPS', 'UPS'),
        ('OTHER', 'Autre'),
    ])
    tracking_number = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    
    # Délais d'inspection
    inspection_days = models.PositiveIntegerField(default=5, help_text="Jours d'inspection (3-7)")
    inspection_deadline = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Détails International"
        verbose_name_plural = "Détails Internationaux"
    
    def __str__(self):
        return f"International: {self.transaction.transaction_id} - {self.buyer_currency}/{self.seller_currency}"
    
    def save(self, *args, **kwargs):
        if not self.inspection_deadline and self.transaction.delivered_at:
            from datetime import timedelta
            self.inspection_deadline = self.transaction.delivered_at + timedelta(days=self.inspection_days)
        super().save(*args, **kwargs)


class Proof(TimeStampedModel):
    """Preuves de livraison et documents associés avec géolocalisation"""
    PROOF_TYPE_CHOICES = [
        ('DELIVERY_PHOTO', 'Photo de livraison'),
        ('RECEIPT', 'Reçu'),
        ('SIGNATURE', 'Signature'),
        ('TRACKING', 'Numéro de suivi'),
        ('INVOICE', 'Facture'),
        ('WARRANTY', 'Garantie'),
        ('FACE_TO_FACE_INITIAL', 'Preuve initiale face-à-face'),
        ('FACE_TO_FACE_FINAL', 'Preuve finale face-à-face'),
        ('MILESTONE_PROOF', 'Preuve de jalon'),
        ('INTERNATIONAL_DOC', 'Document international'),
        ('OTHER', 'Autre'),
    ]
    
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='proofs')
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, null=True, blank=True, related_name='proofs')
    
    proof_type = models.CharField(max_length=20, choices=PROOF_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Fichier et contenu
    file = models.FileField(upload_to='proofs/%Y/%m/%d/', null=True, blank=True)
    text_content = models.TextField(blank=True)
    
    # Géolocalisation
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_address = models.CharField(max_length=255, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True, help_text="Précision GPS en mètres")
    
    # Métadonnées
    metadata = models.JSONField(default=dict, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_proofs')
    
    # Vérification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_proofs')
    verification_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Preuve"
        verbose_name_plural = "Preuves"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction', 'proof_type']),
            models.Index(fields=['milestone', 'proof_type']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.transaction.transaction_id} - {self.get_proof_type_display()}: {self.title}"
    
    def has_location(self):
        """Vérifier si la preuve a une géolocalisation"""
        return self.latitude is not None and self.longitude is not None
    
    def get_location_display(self):
        """Obtenir l'affichage de la localisation"""
        if self.has_location():
            return f"{self.latitude}, {self.longitude}"
        return self.location_address or "Localisation non disponible"