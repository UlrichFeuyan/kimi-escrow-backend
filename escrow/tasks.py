from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

from .models import EscrowTransaction, Milestone
from core.utils import send_notification_email
from users.services import sms_service

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def send_transaction_notification(transaction_id, event_type, message, user_id=None):
    """Envoyer une notification pour un événement de transaction"""
    try:
        transaction_obj = EscrowTransaction.objects.get(id=transaction_id)
        
        # Déterminer les destinataires
        if user_id:
            recipients = [User.objects.get(id=user_id)]
        else:
            recipients = [transaction_obj.buyer, transaction_obj.seller]
        
        for user in recipients:
            # Email notification
            if user.email:
                subject = f"Kimi Escrow - {transaction_obj.transaction_id}"
                send_notification_email(user.email, subject, message)
            
            # SMS notification si activé
            if hasattr(user, 'profile') and user.profile.sms_notifications:
                sms_message = f"Kimi Escrow: {message[:140]}"  # Limiter à 140 caractères
                sms_service.send_notification_sms(user.phone_number, sms_message)
        
        logger.info(f"Notifications envoyées pour transaction {transaction_id}: {event_type}")
        
    except Exception as e:
        logger.error(f"Erreur envoi notification transaction {transaction_id}: {e}")


@shared_task
def send_milestone_notification(milestone_id, event_type, message):
    """Envoyer une notification pour un événement de jalon"""
    try:
        milestone = Milestone.objects.select_related('transaction').get(id=milestone_id)
        transaction_obj = milestone.transaction
        
        # Notifier les deux participants
        recipients = [transaction_obj.buyer, transaction_obj.seller]
        
        for user in recipients:
            if user.email:
                subject = f"Kimi Escrow - Jalon {milestone.title}"
                send_notification_email(user.email, subject, message)
        
        logger.info(f"Notifications envoyées pour jalon {milestone_id}: {event_type}")
        
    except Exception as e:
        logger.error(f"Erreur envoi notification jalon {milestone_id}: {e}")


@shared_task
def process_escrow_payment(transaction_id, action):
    """Traiter un paiement escrow (collecte ou libération)"""
    try:
        transaction_obj = EscrowTransaction.objects.get(id=transaction_id)
        
        if action == 'collect':
            # Collecter les fonds depuis le mobile money
            result = _collect_funds(transaction_obj)
            
            if result['success']:
                transaction_obj.status = 'FUNDS_HELD'
                transaction_obj.funds_received_at = timezone.now()
                transaction_obj.save()
                
                send_transaction_notification.delay(
                    transaction_id,
                    'funds_collected',
                    f"Fonds collectés avec succès pour {transaction_obj.title}"
                )
            else:
                send_transaction_notification.delay(
                    transaction_id,
                    'funds_collection_failed',
                    f"Échec de la collecte des fonds: {result['error']}"
                )
        
        elif action == 'release':
            # Libérer les fonds vers le vendeur
            result = _release_funds(transaction_obj)
            
            if result['success']:
                send_transaction_notification.delay(
                    transaction_id,
                    'funds_released',
                    f"Fonds libérés avec succès pour {transaction_obj.title}"
                )
            else:
                send_transaction_notification.delay(
                    transaction_id,
                    'funds_release_failed',
                    f"Échec de la libération des fonds: {result['error']}"
                )
        
        elif action == 'refund':
            # Rembourser les fonds à l'acheteur
            result = _refund_funds(transaction_obj)
            
            if result['success']:
                transaction_obj.status = 'REFUNDED'
                transaction_obj.save()
                
                send_transaction_notification.delay(
                    transaction_id,
                    'funds_refunded',
                    f"Fonds remboursés avec succès pour {transaction_obj.title}"
                )
        
    except Exception as e:
        logger.error(f"Erreur traitement paiement escrow {transaction_id}: {e}")


@shared_task
def auto_release_funds(transaction_id):
    """Libération automatique des fonds après expiration du délai"""
    try:
        transaction_obj = EscrowTransaction.objects.get(id=transaction_id)
        
        # Vérifier que la transaction est toujours dans l'état DELIVERED
        if transaction_obj.status == 'DELIVERED' and transaction_obj.should_auto_release():
            transaction_obj.status = 'RELEASED'
            transaction_obj.released_at = timezone.now()
            transaction_obj.save()
            
            # Traiter la libération des fonds
            process_escrow_payment.delay(transaction_id, 'release')
            
            send_transaction_notification.delay(
                transaction_id,
                'auto_released',
                f"Fonds libérés automatiquement pour {transaction_obj.title}"
            )
            
            logger.info(f"Libération automatique des fonds pour transaction {transaction_id}")
        
    except EscrowTransaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} non trouvée pour libération automatique")
    except Exception as e:
        logger.error(f"Erreur libération automatique {transaction_id}: {e}")


@shared_task
def check_overdue_transactions():
    """Vérifier les transactions en retard"""
    try:
        now = timezone.now()
        
        # Transactions en attente de paiement en retard
        overdue_payment = EscrowTransaction.objects.filter(
            status='PENDING_FUNDS',
            payment_deadline__lt=now
        )
        
        for transaction_obj in overdue_payment:
            send_transaction_notification.delay(
                transaction_obj.id,
                'payment_overdue',
                f"Paiement en retard pour {transaction_obj.title}. Délai dépassé."
            )
        
        # Transactions en attente de livraison en retard
        overdue_delivery = EscrowTransaction.objects.filter(
            status='FUNDS_HELD',
            delivery_deadline__lt=now
        )
        
        for transaction_obj in overdue_delivery:
            send_transaction_notification.delay(
                transaction_obj.id,
                'delivery_overdue',
                f"Livraison en retard pour {transaction_obj.title}. Délai dépassé."
            )
        
        logger.info(f"Vérification des retards: {overdue_payment.count()} paiements, {overdue_delivery.count()} livraisons")
        
    except Exception as e:
        logger.error(f"Erreur vérification transactions en retard: {e}")


@shared_task
def send_payment_reminders():
    """Envoyer des rappels de paiement"""
    try:
        # Rappels 24h avant expiration
        tomorrow = timezone.now() + timedelta(days=1)
        
        pending_transactions = EscrowTransaction.objects.filter(
            status='PENDING_FUNDS',
            payment_deadline__date=tomorrow.date()
        )
        
        for transaction_obj in pending_transactions:
            send_transaction_notification.delay(
                transaction_obj.id,
                'payment_reminder',
                f"Rappel: Paiement requis dans 24h pour {transaction_obj.title}",
                user_id=transaction_obj.buyer.id
            )
        
        logger.info(f"Rappels de paiement envoyés pour {pending_transactions.count()} transactions")
        
    except Exception as e:
        logger.error(f"Erreur envoi rappels de paiement: {e}")


@shared_task
def send_delivery_reminders():
    """Envoyer des rappels de livraison"""
    try:
        # Rappels 24h avant expiration
        tomorrow = timezone.now() + timedelta(days=1)
        
        held_transactions = EscrowTransaction.objects.filter(
            status='FUNDS_HELD',
            delivery_deadline__date=tomorrow.date()
        )
        
        for transaction_obj in held_transactions:
            send_transaction_notification.delay(
                transaction_obj.id,
                'delivery_reminder',
                f"Rappel: Livraison requise dans 24h pour {transaction_obj.title}",
                user_id=transaction_obj.seller.id
            )
        
        logger.info(f"Rappels de livraison envoyés pour {held_transactions.count()} transactions")
        
    except Exception as e:
        logger.error(f"Erreur envoi rappels de livraison: {e}")


def _collect_funds(transaction):
    """Collecter les fonds depuis le mobile money"""
    try:
        # Intégration avec l'API de paiement mobile
        # Cette fonction sera implémentée avec l'API réelle
        
        # Simulation pour le développement
        import random
        success = random.choice([True, True, True, False])  # 75% de succès
        
        if success:
            return {'success': True, 'transaction_id': f"PAY_{transaction.id}_{timezone.now().timestamp()}"}
        else:
            return {'success': False, 'error': 'Fonds insuffisants'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _release_funds(transaction):
    """Libérer les fonds vers le vendeur"""
    try:
        # Intégration avec l'API bancaire/mobile money
        # Cette fonction sera implémentée avec l'API réelle
        
        # Simulation pour le développement
        import random
        success = random.choice([True, True, True, True, False])  # 80% de succès
        
        if success:
            return {'success': True, 'transaction_id': f"REL_{transaction.id}_{timezone.now().timestamp()}"}
        else:
            return {'success': False, 'error': 'Erreur de traitement bancaire'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _refund_funds(transaction):
    """Rembourser les fonds à l'acheteur"""
    try:
        # Intégration avec l'API bancaire/mobile money
        # Cette fonction sera implémentée avec l'API réelle
        
        # Simulation pour le développement
        import random
        success = random.choice([True, True, True, True, False])  # 80% de succès
        
        if success:
            return {'success': True, 'transaction_id': f"REF_{transaction.id}_{timezone.now().timestamp()}"}
        else:
            return {'success': False, 'error': 'Erreur de traitement bancaire'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
