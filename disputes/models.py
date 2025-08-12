from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import TimeStampedModel
from core.utils import generate_dispute_id
from escrow.models import EscrowTransaction

User = get_user_model()


class Dispute(TimeStampedModel):
    """Modèle pour les litiges"""
    STATUS_CHOICES = [
        ('OPEN', 'Ouvert'),
        ('ASSIGNED', 'Assigné'),
        ('IN_REVIEW', 'En cours d\'examen'),
        ('RESOLVED', 'Résolu'),
        ('CLOSED', 'Fermé'),
        ('ESCALATED', 'Escaladé'),
    ]
    
    CATEGORY_CHOICES = [
        ('DELIVERY_ISSUE', 'Problème de livraison'),
        ('QUALITY_ISSUE', 'Problème de qualité'),
        ('PAYMENT_ISSUE', 'Problème de paiement'),
        ('COMMUNICATION_ISSUE', 'Problème de communication'),
        ('FRAUD', 'Fraude'),
        ('OTHER', 'Autre'),
    ]
    
    VERDICT_CHOICES = [
        ('BUYER_FAVOR', 'En faveur de l\'acheteur'),
        ('SELLER_FAVOR', 'En faveur du vendeur'),
        ('PARTIAL_REFUND', 'Remboursement partiel'),
        ('NO_FAULT', 'Aucune faute'),
    ]
    
    # Identifiants
    dispute_id = models.CharField(max_length=20, unique=True, default=generate_dispute_id)
    
    # Relations
    transaction = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name='dispute')
    complainant = models.ForeignKey(User, on_delete=models.PROTECT, related_name='filed_disputes')
    respondent = models.ForeignKey(User, on_delete=models.PROTECT, related_name='disputes_against')
    arbitre = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='arbitrated_disputes')
    
    # Détails du litige
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    evidence_description = models.TextField(blank=True)
    
    # Statut et résolution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Dates importantes
    assigned_at = models.DateTimeField(null=True, blank=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Priorité
    priority = models.CharField(max_length=10, choices=[
        ('LOW', 'Basse'),
        ('MEDIUM', 'Moyenne'),
        ('HIGH', 'Haute'),
        ('URGENT', 'Urgente'),
    ], default='MEDIUM')
    
    class Meta:
        verbose_name = "Litige"
        verbose_name_plural = "Litiges"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dispute_id']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['arbitre', 'status']),
            models.Index(fields=['complainant']),
            models.Index(fields=['respondent']),
        ]
    
    def __str__(self):
        return f"{self.dispute_id} - {self.title}"
    
    def assign_arbitre(self, arbitre):
        """Assigner un arbitre au litige"""
        self.arbitre = arbitre
        self.status = 'ASSIGNED'
        self.assigned_at = timezone.now()
        self.save(update_fields=['arbitre', 'status', 'assigned_at'])
    
    def start_review(self):
        """Commencer l'examen du litige"""
        if self.status == 'ASSIGNED':
            self.status = 'IN_REVIEW'
            self.review_started_at = timezone.now()
            self.save(update_fields=['status', 'review_started_at'])
    
    def resolve(self, verdict, resolution_notes, refund_amount=None):
        """Résoudre le litige"""
        self.verdict = verdict
        self.resolution_notes = resolution_notes
        self.refund_amount = refund_amount
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.save(update_fields=['verdict', 'resolution_notes', 'refund_amount', 'status', 'resolved_at'])
    
    def can_be_assigned_to(self, arbitre):
        """Vérifier si le litige peut être assigné à cet arbitre"""
        return (arbitre.role == 'ARBITRE' and 
                arbitre.kyc_status == 'VERIFIED' and
                arbitre != self.complainant and 
                arbitre != self.respondent)


class DisputeEvidence(TimeStampedModel):
    """Preuves soumises dans un litige"""
    EVIDENCE_TYPE_CHOICES = [
        ('DOCUMENT', 'Document'),
        ('PHOTO', 'Photo'),
        ('VIDEO', 'Vidéo'),
        ('AUDIO', 'Audio'),
        ('MESSAGE', 'Message/Conversation'),
        ('OTHER', 'Autre'),
    ]
    
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='evidences')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_evidences')
    
    # Type et contenu
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Fichier
    file = models.FileField(upload_to='dispute_evidence/%Y/%m/%d/', null=True, blank=True)
    
    # Métadonnées
    file_size = models.PositiveIntegerField(null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)
    
    class Meta:
        verbose_name = "Preuve de Litige"
        verbose_name_plural = "Preuves de Litige"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.dispute.dispute_id} - {self.title}"


class DisputeComment(TimeStampedModel):
    """Commentaires et communications dans un litige"""
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dispute_comments')
    
    # Contenu
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)  # Visible seulement par l'arbitre et admins
    
    # Pièce jointe
    attachment = models.FileField(upload_to='dispute_attachments/%Y/%m/%d/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Commentaire de Litige"
        verbose_name_plural = "Commentaires de Litige"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.dispute.dispute_id} - Commentaire de {self.author.get_full_name()}"


class DisputeResolution(TimeStampedModel):
    """Résolution détaillée d'un litige"""
    dispute = models.OneToOneField(Dispute, on_delete=models.CASCADE, related_name='resolution')
    
    # Détails de la résolution
    summary = models.TextField()
    reasoning = models.TextField()
    
    # Actions recommandées
    buyer_action = models.TextField(blank=True)
    seller_action = models.TextField(blank=True)
    
    # Pénalités
    buyer_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    seller_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Satisfaction
    complainant_satisfied = models.BooleanField(null=True, blank=True)
    respondent_satisfied = models.BooleanField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Résolution de Litige"
        verbose_name_plural = "Résolutions de Litige"
    
    def __str__(self):
        return f"Résolution {self.dispute.dispute_id}"