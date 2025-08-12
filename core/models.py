from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    """
    Modèle abstrait qui fournit les champs created_at et updated_at
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """
    Modèle pour l'audit trail de toutes les actions sensibles
    """
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('PAYMENT', 'Paiement'),
        ('TRANSFER', 'Transfert'),
        ('DISPUTE', 'Litige'),
        ('KYC', 'Vérification KYC'),
        ('ADMIN', 'Action Admin'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100)  # Ex: 'EscrowTransaction', 'User'
    resource_id = models.CharField(max_length=100, null=True, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource_type} at {self.timestamp}"


class GlobalSettings(models.Model):
    """
    Paramètres globaux de l'application
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètre Global"
        verbose_name_plural = "Paramètres Globaux"

    def __str__(self):
        return f"{self.key}: {self.value}"
