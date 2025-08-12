from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.storage import default_storage
import logging
import os

from .models import KYCDocument
from .services import sms_service, smile_id_service
from core.utils import send_notification_email

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_verification_sms(self, user_id: int, verification_code: str):
    """
    Tâche asynchrone pour envoyer un SMS de vérification
    """
    try:
        user = User.objects.get(id=user_id)
        success = sms_service.send_verification_sms(user.phone_number, verification_code)
        
        if success:
            logger.info(f"SMS de vérification envoyé à {user.phone_number}")
            return f"SMS envoyé avec succès à {user.phone_number}"
        else:
            logger.error(f"Échec envoi SMS à {user.phone_number}")
            raise Exception("Échec envoi SMS")
            
    except User.DoesNotExist:
        logger.error(f"Utilisateur {user_id} non trouvé pour l'envoi SMS")
        return "Utilisateur non trouvé"
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi SMS: {e}")
        # Retry avec backoff exponentiel
        raise self.retry(countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def process_kyc_document(self, document_id: int):
    """
    Tâche asynchrone pour traiter un document KYC avec Smile ID
    """
    try:
        document = KYCDocument.objects.get(id=document_id)
        user = document.user
        
        # Mettre à jour le statut
        document.status = 'PROCESSING'
        document.save(update_fields=['status'])
        
        # Préparer les données pour Smile ID
        file_path = document.file.path
        
        # Encoder l'image en base64
        encoded_image = smile_id_service.encode_image_to_base64(file_path)
        if not encoded_image:
            raise Exception("Impossible d'encoder l'image")
        
        # Préparer les informations d'identité
        id_info = {
            "country": "CM",  # Cameroun
            "id_type": "NATIONAL_ID" if document.document_type.startswith('ID_') else "PASSPORT",
            "id_number": user.id_card_number or "",
            "first_name": user.first_name,
            "last_name": user.last_name,
            "dob": user.date_of_birth.isoformat() if user.date_of_birth else "",
        }
        
        # Soumettre le job à Smile ID
        if document.document_type == 'SELFIE':
            # Pour les selfies, on fait juste une vérification de vivacité
            result = smile_id_service.submit_job(
                user_id=str(user.id),
                job_type="biometric_kyc",
                images=[{
                    "image_type_id": 2,  # Selfie
                    "image": encoded_image
                }]
            )
        else:
            # Pour les documents d'identité
            result = smile_id_service.submit_job(
                user_id=str(user.id),
                job_type="document_verification",
                id_info=id_info,
                images=[{
                    "image_type_id": 1,  # Document
                    "image": encoded_image
                }]
            )
        
        if result and result.get('success'):
            document.smile_id_job_id = result.get('job_id', '')
            document.smile_id_result = result
            document.status = 'PROCESSING'
            document.save(update_fields=['smile_id_job_id', 'smile_id_result', 'status'])
            
            logger.info(f"Document KYC {document_id} soumis à Smile ID avec succès")
            
            # Programmer une vérification du statut dans 30 secondes
            check_kyc_job_status.apply_async(
                args=[document.id],
                countdown=30
            )
            
        else:
            document.status = 'REJECTED'
            document.verification_notes = "Erreur lors de la soumission à Smile ID"
            document.save(update_fields=['status', 'verification_notes'])
            
            logger.error(f"Erreur soumission Smile ID pour document {document_id}")
            
    except KYCDocument.DoesNotExist:
        logger.error(f"Document KYC {document_id} non trouvé")
        return "Document non trouvé"
    except Exception as e:
        logger.error(f"Erreur traitement document KYC {document_id}: {e}")
        # Retry avec backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=5)
def check_kyc_job_status(self, document_id: int):
    """
    Vérifier le statut d'un job KYC sur Smile ID
    """
    try:
        document = KYCDocument.objects.get(id=document_id)
        
        if not document.smile_id_job_id:
            logger.error(f"Pas de job ID Smile ID pour le document {document_id}")
            return
        
        # Obtenir le statut du job
        result = smile_id_service.get_job_status(document.smile_id_job_id)
        
        if result:
            job_complete = result.get('job_complete', False)
            job_success = result.get('job_success', False)
            
            if job_complete:
                # Le job est terminé
                if job_success:
                    document.status = 'VERIFIED'
                    document.confidence_score = result.get('confidence', 0)
                    document.verification_notes = "Vérifié avec succès par Smile ID"
                else:
                    document.status = 'REJECTED'
                    document.verification_notes = f"Rejeté par Smile ID: {result.get('code', 'Raison inconnue')}"
                
                document.smile_id_result = result
                document.save(update_fields=['status', 'confidence_score', 'verification_notes', 'smile_id_result'])
                
                # Vérifier si tous les documents requis sont vérifiés
                check_overall_kyc_status.delay(document.user.id)
                
                logger.info(f"Statut KYC mis à jour pour document {document_id}: {document.status}")
                
            else:
                # Le job n'est pas encore terminé, reprogrammer une vérification
                if self.request.retries < 5:
                    raise self.retry(countdown=60)  # Retry dans 1 minute
                else:
                    # Trop de tentatives, marquer comme timeout
                    document.status = 'REJECTED'
                    document.verification_notes = "Timeout lors de la vérification Smile ID"
                    document.save(update_fields=['status', 'verification_notes'])
        else:
            # Erreur API, retry
            raise self.retry(countdown=120)
            
    except KYCDocument.DoesNotExist:
        logger.error(f"Document KYC {document_id} non trouvé")
    except Exception as e:
        logger.error(f"Erreur vérification statut KYC {document_id}: {e}")
        if self.request.retries < 5:
            raise self.retry(countdown=60 * (2 ** self.request.retries))


@shared_task
def check_overall_kyc_status(user_id: int):
    """
    Vérifier le statut KYC global d'un utilisateur
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Documents requis
        required_docs = ['ID_FRONT', 'ID_BACK', 'SELFIE', 'PROOF_OF_ADDRESS']
        
        # Vérifier que tous les documents requis sont vérifiés
        verified_docs = KYCDocument.objects.filter(
            user=user,
            document_type__in=required_docs,
            status='VERIFIED'
        ).values_list('document_type', flat=True)
        
        if set(verified_docs) >= set(required_docs):
            # Tous les documents sont vérifiés
            user.kyc_status = 'UNDER_REVIEW'  # En attente d'approbation manuelle
            user.save(update_fields=['kyc_status'])
            
            # Notifier les admins
            notify_admins_kyc_ready.delay(user_id)
            
            # Notifier l'utilisateur
            if user.email:
                send_notification_email(
                    user.email,
                    "Documents KYC vérifiés",
                    "Tous vos documents ont été vérifiés avec succès. Votre dossier est maintenant en cours de révision par notre équipe."
                )
            
            logger.info(f"Utilisateur {user_id} - Tous les documents KYC vérifiés")
            
        elif KYCDocument.objects.filter(user=user, status='REJECTED').exists():
            # Au moins un document a été rejeté
            user.kyc_status = 'REJECTED'
            user.save(update_fields=['kyc_status'])
            
            # Notifier l'utilisateur
            if user.email:
                send_notification_email(
                    user.email,
                    "Documents KYC rejetés",
                    "Un ou plusieurs de vos documents ont été rejetés. Veuillez vous connecter à votre compte pour voir les détails et soumettre de nouveaux documents."
                )
            
            logger.info(f"Utilisateur {user_id} - Documents KYC rejetés")
            
    except User.DoesNotExist:
        logger.error(f"Utilisateur {user_id} non trouvé pour vérification KYC")
    except Exception as e:
        logger.error(f"Erreur vérification KYC globale pour utilisateur {user_id}: {e}")


@shared_task
def notify_admins_kyc_ready(user_id: int):
    """
    Notifier les admins qu'un KYC est prêt pour révision
    """
    try:
        user = User.objects.get(id=user_id)
        admins = User.objects.filter(role='ADMIN', is_active=True)
        
        subject = f"Nouveau KYC à réviser - {user.get_full_name()}"
        message = f"""
        Un nouveau dossier KYC est prêt pour révision:
        
        Utilisateur: {user.get_full_name()}
        Téléphone: {user.phone_number}
        Email: {user.email or 'Non fourni'}
        Date de soumission: {timezone.now().strftime('%d/%m/%Y %H:%M')}
        
        Veuillez vous connecter à l'interface d'administration pour réviser ce dossier.
        """
        
        for admin in admins:
            if admin.email:
                send_notification_email(admin.email, subject, message)
        
        logger.info(f"Admins notifiés pour KYC utilisateur {user_id}")
        
    except User.DoesNotExist:
        logger.error(f"Utilisateur {user_id} non trouvé pour notification admin")
    except Exception as e:
        logger.error(f"Erreur notification admins KYC {user_id}: {e}")


@shared_task
def send_kyc_reminder():
    """
    Envoyer des rappels KYC aux utilisateurs non vérifiés
    """
    try:
        # Utilisateurs avec KYC en attente depuis plus de 3 jours
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=3)
        
        users_to_remind = User.objects.filter(
            kyc_status='PENDING',
            created_at__lte=cutoff_date,
            is_active=True
        )
        
        for user in users_to_remind:
            if user.email:
                send_notification_email(
                    user.email,
                    "Rappel - Vérification d'identité requise",
                    f"Bonjour {user.first_name},\n\nVotre compte Kimi Escrow nécessite une vérification d'identité pour utiliser nos services de transaction sécurisée.\n\nConnectez-vous à votre compte pour télécharger vos documents."
                )
            
            # Aussi envoyer un SMS si possible
            sms_service.send_notification_sms(
                user.phone_number,
                "Kimi Escrow: Votre vérification d'identité est requise pour utiliser nos services. Connectez-vous à votre compte."
            )
        
        logger.info(f"Rappels KYC envoyés à {users_to_remind.count()} utilisateurs")
        
    except Exception as e:
        logger.error(f"Erreur envoi rappels KYC: {e}")


@shared_task
def cleanup_expired_verification_tokens():
    """
    Nettoyer les tokens de vérification expirés
    """
    try:
        now = timezone.now()
        
        # Nettoyer les tokens de vérification SMS expirés
        expired_count = User.objects.filter(
            phone_verification_expires_at__lt=now,
            is_phone_verified=False
        ).update(
            phone_verification_token='',
            phone_verification_expires_at=None
        )
        
        logger.info(f"Nettoyage des tokens expirés: {expired_count} tokens supprimés")
        
    except Exception as e:
        logger.error(f"Erreur nettoyage tokens expirés: {e}")
