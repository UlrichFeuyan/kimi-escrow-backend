import requests
import logging
from django.conf import settings
from typing import Dict, Any, Optional
import json
import base64

logger = logging.getLogger(__name__)


class SmileIDService:
    """
    Service d'intégration avec l'API Smile ID pour la vérification KYC
    """
    
    def __init__(self):
        self.partner_id = settings.SMILE_ID_PARTNER_ID
        self.api_key = settings.SMILE_ID_API_KEY
        self.base_url = settings.SMILE_ID_BASE_URL
        self.sandbox = settings.SMILE_ID_SANDBOX
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtenir les headers pour les requêtes API"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'SmileId-Partner-Id': self.partner_id,
        }
    
    def submit_job(self, user_id: str, job_type: str = "enhanced_kyc", 
                   id_info: Dict = None, images: Dict = None) -> Optional[Dict]:
        """
        Soumettre un job de vérification à Smile ID
        
        Args:
            user_id: ID de l'utilisateur
            job_type: Type de vérification ('enhanced_kyc', 'document_verification', etc.)
            id_info: Informations d'identité
            images: Images encodées en base64
        
        Returns:
            Dict contenant la réponse de l'API ou None en cas d'erreur
        """
        url = f"{self.base_url}/submit_job"
        
        payload = {
            "partner_id": self.partner_id,
            "job_type": job_type,
            "user_id": user_id,
            "callback_url": f"{settings.ALLOWED_HOSTS[0]}/api/kyc/webhook/smile-id/",
            "use_enrolled_image": False,
            "allow_re_enrollment": True,
        }
        
        if id_info:
            payload["id_info"] = id_info
        
        if images:
            payload["images"] = images
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Smile ID job submitted successfully for user {user_id}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la soumission du job Smile ID: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON Smile ID: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Obtenir le statut d'un job Smile ID
        
        Args:
            job_id: ID du job
        
        Returns:
            Dict contenant le statut du job ou None en cas d'erreur
        """
        url = f"{self.base_url}/job_status"
        
        payload = {
            "partner_id": self.partner_id,
            "job_id": job_id,
        }
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération du statut Smile ID: {e}")
            return None
    
    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        Encoder une image en base64 pour Smile ID
        
        Args:
            image_path: Chemin vers l'image
        
        Returns:
            String base64 ou None en cas d'erreur
        """
        try:
            with open(image_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            logger.error(f"Erreur encodage image: {e}")
            return None
    
    def verify_document(self, user_id: str, document_image: str, 
                       selfie_image: str, id_info: Dict) -> Optional[Dict]:
        """
        Vérifier un document d'identité avec selfie
        
        Args:
            user_id: ID de l'utilisateur
            document_image: Image du document encodée en base64
            selfie_image: Image selfie encodée en base64
            id_info: Informations du document
        
        Returns:
            Dict contenant le résultat de la vérification
        """
        images = [
            {
                "image_type_id": 1,  # Document front
                "image": document_image
            },
            {
                "image_type_id": 2,  # Selfie
                "image": selfie_image
            }
        ]
        
        return self.submit_job(
            user_id=user_id,
            job_type="enhanced_kyc",
            id_info=id_info,
            images=images
        )
    
    def parse_webhook_result(self, webhook_data: Dict) -> Dict:
        """
        Parser les résultats du webhook Smile ID
        
        Args:
            webhook_data: Données reçues du webhook
        
        Returns:
            Dict contenant les informations parsées
        """
        try:
            result = {
                'job_id': webhook_data.get('job_id'),
                'user_id': webhook_data.get('user_id'),
                'job_success': webhook_data.get('job_success', False),
                'code': webhook_data.get('code'),
                'confidence': webhook_data.get('confidence', 0),
                'smile_job_id': webhook_data.get('smile_job_id'),
            }
            
            # Extraire les résultats de vérification
            if 'result' in webhook_data:
                result_data = webhook_data['result']
                result.update({
                    'id_verification': result_data.get('id_verification', {}),
                    'selfie_verification': result_data.get('selfie_verification', {}),
                    'liveness_check': result_data.get('liveness_check', {}),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur parsing webhook Smile ID: {e}")
            return {'job_success': False, 'error': str(e)}


class SMSService:
    """
    Service d'envoi de SMS pour la vérification
    """
    
    def __init__(self):
        # Configuration pour le service SMS (exemple avec une API SMS camerounaise)
        self.api_url = getattr(settings, 'SMS_API_URL', '')
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'KIMI-ESCROW')
    
    def send_verification_sms(self, phone_number: str, verification_code: str) -> bool:
        """
        Envoyer un SMS de vérification
        
        Args:
            phone_number: Numéro de téléphone au format international
            verification_code: Code de vérification à 6 chiffres
        
        Returns:
            True si envoyé avec succès, False sinon
        """
        message = f"Votre code de vérification Kimi Escrow est: {verification_code}. Ce code expire dans 10 minutes."
        
        try:
            # En mode développement, on log le code au lieu d'envoyer un vrai SMS
            if settings.DEBUG:
                logger.info(f"SMS CODE for {phone_number}: {verification_code}")
                return True
            
            # Configuration pour une vraie API SMS (exemple)
            payload = {
                'to': phone_number,
                'message': message,
                'sender_id': self.sender_id,
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"SMS envoyé avec succès à {phone_number}")
                return True
            else:
                logger.error(f"Erreur envoi SMS: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du SMS: {e}")
            return False
    
    def send_notification_sms(self, phone_number: str, message: str) -> bool:
        """
        Envoyer un SMS de notification
        
        Args:
            phone_number: Numéro de téléphone
            message: Message à envoyer
        
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            if settings.DEBUG:
                logger.info(f"SMS NOTIFICATION to {phone_number}: {message}")
                return True
            
            payload = {
                'to': phone_number,
                'message': message,
                'sender_id': self.sender_id,
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erreur envoi SMS notification: {e}")
            return False


# Instances globales des services
smile_id_service = SmileIDService()
sms_service = SMSService()
