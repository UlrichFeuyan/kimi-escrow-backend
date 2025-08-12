import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware pour l'audit trail automatique des actions sensibles
    """
    
    SENSITIVE_PATHS = [
        '/api/auth/',
        '/api/escrow/',
        '/api/payments/',
        '/api/disputes/',
        '/admin/',
    ]
    
    SENSITIVE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_request(self, request):
        # Stocker les informations de la requête pour l'audit
        request._audit_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'method': request.method,
            'path': request.path,
        }
        
        # Log de connexion
        if request.path == '/api/auth/login/' and request.method == 'POST':
            try:
                body = json.loads(request.body) if request.body else {}
                phone_number = body.get('phone_number', 'Unknown')
                AuditLog.objects.create(
                    user=None,
                    action='LOGIN',
                    resource_type='Authentication',
                    details={'phone_number': phone_number, 'attempt': True},
                    ip_address=request._audit_data['ip_address'],
                    user_agent=request._audit_data['user_agent'],
                )
            except Exception as e:
                logger.error(f"Erreur audit connexion: {e}")
    
    def process_response(self, request, response):
        # Audit pour les requêtes sensibles
        if (hasattr(request, '_audit_data') and 
            any(path in request.path for path in self.SENSITIVE_PATHS) and
            request.method in self.SENSITIVE_METHODS and
            hasattr(request, 'user') and 
            request.user.is_authenticated):
            
            try:
                self.create_audit_log(request, response)
            except Exception as e:
                logger.error(f"Erreur création audit log: {e}")
        
        return response
    
    def create_audit_log(self, request, response):
        """Créer un log d'audit pour l'action"""
        action = self.get_action_type(request)
        resource_type = self.get_resource_type(request.path)
        
        # Extraire l'ID de la ressource depuis l'URL si possible
        resource_id = self.extract_resource_id(request.path)
        
        details = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
        }
        
        # Ajouter des détails spécifiques selon le type d'action
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, '_body') and request._body:
                    body = json.loads(request._body)
                    # Filtrer les informations sensibles
                    filtered_body = self.filter_sensitive_data(body)
                    details['request_data'] = filtered_body
            except (json.JSONDecodeError, AttributeError):
                pass
        
        AuditLog.objects.create(
            user=request.user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request._audit_data.get('ip_address'),
            user_agent=request._audit_data.get('user_agent'),
        )
    
    def get_action_type(self, request):
        """Déterminer le type d'action basé sur la méthode HTTP"""
        method_mapping = {
            'POST': 'CREATE',
            'PUT': 'UPDATE',
            'PATCH': 'UPDATE',
            'DELETE': 'DELETE',
        }
        return method_mapping.get(request.method, 'UPDATE')
    
    def get_resource_type(self, path):
        """Déterminer le type de ressource basé sur le chemin"""
        if '/escrow/' in path:
            return 'EscrowTransaction'
        elif '/payments/' in path:
            return 'Payment'
        elif '/disputes/' in path:
            return 'Dispute'
        elif '/auth/' in path:
            return 'Authentication'
        elif '/admin/' in path:
            return 'AdminAction'
        else:
            return 'Unknown'
    
    def extract_resource_id(self, path):
        """Extraire l'ID de la ressource depuis l'URL"""
        import re
        # Pattern pour capturer les IDs dans les URLs REST
        match = re.search(r'/(\d+)/?$', path)
        if match:
            return match.group(1)
        
        # Pattern pour les UUIDs
        uuid_match = re.search(r'/([a-f0-9-]{36})/?$', path)
        if uuid_match:
            return uuid_match.group(1)
        
        return None
    
    def filter_sensitive_data(self, data):
        """Filtrer les données sensibles des logs"""
        sensitive_fields = [
            'password', 'password_confirmation', 'secret', 'token',
            'api_key', 'private_key', 'card_number', 'cvv', 'pin'
        ]
        
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if any(field in key.lower() for field in sensitive_fields):
                    filtered[key] = '***FILTERED***'
                elif isinstance(value, dict):
                    filtered[key] = self.filter_sensitive_data(value)
                else:
                    filtered[key] = value
            return filtered
        
        return data
    
    def get_client_ip(self, request):
        """Obtenir l'adresse IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
