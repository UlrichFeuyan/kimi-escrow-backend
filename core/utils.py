import uuid
import secrets
import string
from typing import Dict, Any
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def generate_transaction_id():
    """Générer un ID unique pour les transactions"""
    return f"TXN-{uuid.uuid4().hex[:8].upper()}"


def generate_payment_reference():
    """Générer une référence unique pour les paiements"""
    return f"PAY-{uuid.uuid4().hex[:12].upper()}"


def generate_dispute_id():
    """Générer un ID unique pour les litiges"""
    return f"DIS-{uuid.uuid4().hex[:8].upper()}"


def generate_secure_token(length: int = 32) -> str:
    """Générer un token sécurisé"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def calculate_commission(amount: float) -> float:
    """Calculer la commission sur un montant"""
    commission_rate = getattr(settings, 'ESCROW_COMMISSION_RATE', 0.025)
    return amount * commission_rate


def is_amount_valid(amount: float) -> bool:
    """Vérifier si le montant est dans les limites autorisées"""
    min_amount = getattr(settings, 'MINIMUM_ESCROW_AMOUNT', 1000)
    max_amount = getattr(settings, 'MAXIMUM_ESCROW_AMOUNT', 10000000)
    return min_amount <= amount <= max_amount


def send_notification_email(to_email: str, subject: str, message: str, **kwargs) -> bool:
    """Envoyer un email de notification"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
            **kwargs
        )
        logger.info(f"Email envoyé à {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erreur envoi email à {to_email}: {e}")
        return False


def format_amount(amount: float, currency: str = "XAF") -> str:
    """Formater un montant avec la devise"""
    return f"{amount:,.0f} {currency}"


def get_auto_release_date() -> timezone.datetime:
    """Calculer la date de libération automatique"""
    days = getattr(settings, 'AUTO_RELEASE_DAYS', 14)
    return timezone.now() + timedelta(days=days)


def get_dispute_timeout_date() -> timezone.datetime:
    """Calculer la date limite pour créer un litige"""
    days = getattr(settings, 'DISPUTE_TIMEOUT_DAYS', 7)
    return timezone.now() + timedelta(days=days)


def sanitize_phone_number(phone: str) -> str:
    """Normaliser un numéro de téléphone au format camerounais"""
    # Supprimer tous les caractères non numériques
    phone = ''.join(filter(str.isdigit, phone))
    
    # Formats camerounais possibles
    if phone.startswith('237'):
        return f"+{phone}"
    elif phone.startswith('6') and len(phone) == 9:
        return f"+237{phone}"
    elif len(phone) == 9:
        return f"+237{phone}"
    elif len(phone) == 12 and phone.startswith('237'):
        return f"+{phone}"
    
    return phone


def validate_cameroon_phone(phone: str) -> bool:
    """Valider un numéro de téléphone camerounais"""
    normalized = sanitize_phone_number(phone)
    
    # Format: +237XXXXXXXXX (13 caractères total)
    if len(normalized) != 13 or not normalized.startswith('+237'):
        return False
    
    # Le numéro doit commencer par 6 (mobile)
    if not normalized[4] == '6':
        return False
    
    return True


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Masquer les données sensibles en ne gardant que quelques caractères"""
    if len(data) <= visible_chars:
        return '*' * len(data)
    
    return data[:visible_chars] + '*' * (len(data) - visible_chars)


def get_client_ip(request) -> str:
    """Obtenir l'adresse IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def create_api_response(success: bool = True, message: str = "", data: Any = None, 
                       errors: Dict = None, status_code: int = 200) -> Dict:
    """Créer une réponse API standardisée"""
    response = {
        'success': success,
        'message': message,
        'timestamp': timezone.now().isoformat(),
    }
    
    if data is not None:
        response['data'] = data
    
    if errors:
        response['errors'] = errors
    
    return response


def log_api_call(user, endpoint: str, method: str, status_code: int, 
                response_time: float = None, request_data: Dict = None):
    """Logger les appels API"""
    log_data = {
        'user': str(user) if user.is_authenticated else 'Anonymous',
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'timestamp': timezone.now().isoformat(),
    }
    
    if response_time:
        log_data['response_time'] = f"{response_time:.3f}s"
    
    if request_data:
        # Filtrer les données sensibles
        filtered_data = {}
        sensitive_fields = ['password', 'token', 'api_key', 'secret']
        
        for key, value in request_data.items():
            if any(field in key.lower() for field in sensitive_fields):
                filtered_data[key] = '***FILTERED***'
            else:
                filtered_data[key] = value
        
        log_data['request_data'] = filtered_data
    
    logger.info(f"API Call: {log_data}")


class APIResponseMixin:
    """Mixin pour standardiser les réponses API"""
    
    def success_response(self, data=None, message="", status_code=200):
        from rest_framework.response import Response
        return Response(
            create_api_response(True, message, data),
            status=status_code
        )
    
    def error_response(self, message="", errors=None, status_code=400):
        from rest_framework.response import Response
        return Response(
            create_api_response(False, message, errors=errors),
            status=status_code
        )
