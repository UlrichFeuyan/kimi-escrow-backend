from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile, KYCDocument
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Créer automatiquement un profil utilisateur lors de la création d'un utilisateur
    """
    if created:
        try:
            UserProfile.objects.create(user=instance)
            logger.info(f"Profil créé pour l'utilisateur {instance.phone_number}")
        except Exception as e:
            logger.error(f"Erreur création profil pour {instance.phone_number}: {e}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Sauvegarder automatiquement le profil utilisateur
    """
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
    except UserProfile.DoesNotExist:
        # Créer le profil s'il n'existe pas
        UserProfile.objects.create(user=instance)
        logger.info(f"Profil créé pour l'utilisateur existant {instance.phone_number}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde profil pour {instance.phone_number}: {e}")


@receiver(post_save, sender=KYCDocument)
def update_kyc_status_on_document_change(sender, instance, created, **kwargs):
    """
    Mettre à jour le statut KYC de l'utilisateur quand un document change
    """
    try:
        user = instance.user
        
        # Si un document est rejeté, mettre le statut utilisateur en REJECTED
        if instance.status == 'REJECTED' and hasattr(user, 'kyc_status') and user.kyc_status != 'REJECTED':
            user.kyc_status = 'REJECTED'
            user.kyc_rejection_reason = f"Document {instance.get_document_type_display()} rejeté: {instance.verification_notes}"
            user.save(update_fields=['kyc_status', 'kyc_rejection_reason'])
            logger.info(f"Statut KYC utilisateur {user.phone_number} mis à jour: REJECTED")
        
        # Si tous les documents requis sont vérifiés, mettre en UNDER_REVIEW
        elif instance.status == 'VERIFIED':
            required_docs = ['ID_FRONT', 'ID_BACK', 'SELFIE', 'PROOF_OF_ADDRESS']
            verified_docs = KYCDocument.objects.filter(
                user=user,
                document_type__in=required_docs,
                status='VERIFIED'
            ).values_list('document_type', flat=True)
            
            if (set(verified_docs) >= set(required_docs) and 
                hasattr(user, 'kyc_status') and 
                user.kyc_status not in ['VERIFIED', 'UNDER_REVIEW']):
                user.kyc_status = 'UNDER_REVIEW'
                user.save(update_fields=['kyc_status'])
                logger.info(f"Statut KYC utilisateur {user.phone_number} mis à jour: UNDER_REVIEW")
                
                # Notifier les admins (tâche asynchrone)
                try:
                    from .tasks import notify_admins_kyc_ready
                    notify_admins_kyc_ready.delay(user.id)
                except ImportError:
                    logger.warning("Module tasks non disponible pour notifier les admins")
        
    except Exception as e:
        logger.error(f"Erreur mise à jour statut KYC: {e}")


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    """
    Actions avant la sauvegarde d'un utilisateur
    """
    try:
        # Normaliser le numéro de téléphone
        from core.utils import sanitize_phone_number
        if instance.phone_number:
            instance.phone_number = sanitize_phone_number(instance.phone_number)
        
        # Nettoyer l'email
        if instance.email:
            instance.email = instance.email.lower().strip()
        
        # Nettoyer les noms
        if instance.first_name:
            instance.first_name = instance.first_name.strip().title()
        if instance.last_name:
            instance.last_name = instance.last_name.strip().title()
            
    except Exception as e:
        logger.error(f"Erreur pre_save utilisateur: {e}")


@receiver(post_save, sender=User)
def log_user_status_changes(sender, instance, created, **kwargs):
    """
    Logger les changements de statut importants
    """
    try:
        if not created:
            # Vérifier les changements de statut KYC
            if hasattr(instance, '_old_kyc_status'):
                old_status = instance._old_kyc_status
                new_status = instance.kyc_status
                
                if old_status != new_status:
                    logger.info(f"Changement statut KYC pour {instance.phone_number}: {old_status} -> {new_status}")
                    
                    # Créer un log d'audit
                    from core.models import AuditLog
                    AuditLog.objects.create(
                        user=instance,
                        action='UPDATE',
                        resource_type='User',
                        resource_id=str(instance.id),
                        details={
                            'field': 'kyc_status',
                            'old_value': old_status,
                            'new_value': new_status,
                        }
                    )
        
    except Exception as e:
        logger.error(f"Erreur log changement statut: {e}")
