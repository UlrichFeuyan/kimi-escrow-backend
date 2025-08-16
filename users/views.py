from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import hashlib
import logging
import json

from .models import CustomUser, KYCDocument, UserProfile, LoginAttempt
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, PhoneVerificationSerializer,
    UserProfileSerializer, UserProfileUpdateSerializer, KYCDocumentSerializer,
    UserExtendedProfileSerializer, PasswordChangeSerializer, AdminUserSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from core.permissions import IsAdmin
from core.utils import APIResponseMixin, send_notification_email
from .tasks import send_verification_sms, process_kyc_document
from .services import smile_id_service

User = get_user_model()
logger = logging.getLogger(__name__)


class UserRegistrationView(APIView, APIResponseMixin):
    """Endpoint d'inscription des utilisateurs"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Inscription d'un nouvel utilisateur",
        operation_description="""
        Inscription d'un nouvel utilisateur sur la plateforme Kimi Escrow.
        
        **Rôles disponibles:**
        - BUYER: Acheteur (peut créer des transactions escrow)
        - SELLER: Vendeur (peut recevoir des paiements)
        - ARBITRE: Arbitre (peut résoudre les litiges)
        
        **Processus d'inscription:**
        1. Création du compte utilisateur
        2. Envoi d'un SMS de vérification
        3. Création du profil utilisateur
        4. Génération des tokens JWT
        
        **Note:** Le KYC sera requis pour les transactions importantes.
        """,
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Utilisateur créé avec succès",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Utilisateur créé avec succès. Vérifiez votre téléphone pour le code de vérification.",
                        "data": {
                            "user_id": 1,
                            "phone_number": "+237612345678",
                            "first_name": "John",
                            "last_name": "Doe",
                            "role": "BUYER",
                            "kyc_status": "PENDING",
                            "tokens": {
                                "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                            }
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            ),
            400: openapi.Response(
                description="Données d'inscription invalides",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Données d'inscription invalides",
                        "errors": {
                            "phone_number": ["Ce numéro de téléphone est déjà utilisé."]
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Envoyer le SMS de vérification
                    send_verification_sms.delay(user.id, user.phone_verification_token)
                    
                    # Générer les tokens JWT
                    refresh = RefreshToken.for_user(user)
                    
                    return self.success_response({
                        'user': UserProfileSerializer(user).data,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        },
                        'message': 'Inscription réussie. Un SMS de vérification a été envoyé.'
                    }, status_code=status.HTTP_201_CREATED)
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'inscription: {e}")
                return self.error_response(
                    "Erreur lors de l'inscription. Veuillez réessayer.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return self.error_response("Données d'inscription invalides", errors=serializer.errors)


class UserLoginView(TokenObtainPairView, APIResponseMixin):
    """Endpoint de connexion des utilisateurs"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Connexion d'un utilisateur",
        operation_description="""
        Connexion d'un utilisateur existant avec numéro de téléphone et mot de passe.
        
        **Utilisateurs de test disponibles:**
        - **Admin**: +237600000000 / TestPassword123!
        - **Acheteur**: +237612345678 / TestPassword123!
        - **Vendeur**: +237698765432 / TestPassword123!
        - **Arbitre**: +237655555555 / TestPassword123!
        
        **Retourne:**
        - Token d'accès JWT (valide 24h)
        - Token de rafraîchissement (valide 7 jours)
        - Informations utilisateur
        """,
        request_body=UserLoginSerializer,
        responses={
            200: openapi.Response(
                description="Connexion réussie",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Connexion réussie",
                        "data": {
                            "user": {
                                "id": 1,
                                "phone_number": "+237612345678",
                                "first_name": "John",
                                "last_name": "Doe",
                                "role": "BUYER",
                                "kyc_status": "VERIFIED",
                                "is_phone_verified": True
                            },
                            "tokens": {
                                "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                            }
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            ),
            401: openapi.Response(
                description="Identifiants invalides",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Identifiants invalides",
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return self.success_response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': 'Connexion réussie'
            })
        
        return self.error_response(
            "Identifiants invalides",
            errors=serializer.errors,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class PhoneVerificationView(APIView, APIResponseMixin):
    """Endpoint de vérification du numéro de téléphone"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if request.user.is_phone_verified:
            return self.error_response("Numéro déjà vérifié")
        
        serializer = PhoneVerificationSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['verification_code']
            user = request.user
            
            if (user.phone_verification_token == code and
                user.phone_verification_expires_at and
                timezone.now() <= user.phone_verification_expires_at):
                
                user.is_phone_verified = True
                user.phone_verification_token = ''
                user.phone_verification_expires_at = None
                user.save(update_fields=[
                    'is_phone_verified', 
                    'phone_verification_token',
                    'phone_verification_expires_at'
                ])
                
                return self.success_response({'message': 'Numéro de téléphone vérifié avec succès'})
            
            return self.error_response("Code de vérification invalide ou expiré")
        
        return self.error_response("Code de vérification invalide", errors=serializer.errors)


class ResendVerificationView(APIView, APIResponseMixin):
    """Endpoint pour renvoyer le code de vérification SMS"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.is_phone_verified:
            return self.error_response("Numéro déjà vérifié")
        
        # Générer un nouveau code
        token = user.generate_phone_verification_token()
        
        # Envoyer le SMS
        send_verification_sms.delay(user.id, token)
        
        return self.success_response({'message': 'Code de vérification renvoyé'})


class UserProfileView(generics.RetrieveUpdateAPIView, APIResponseMixin):
    """Endpoint pour consulter et modifier le profil utilisateur"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserExtendedProfileSerializer
        return UserProfileUpdateSerializer
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView, APIResponseMixin):
    """Endpoint pour changer le mot de passe"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return self.success_response({'message': 'Mot de passe modifié avec succès'})
        
        return self.error_response("Erreur lors du changement de mot de passe", errors=serializer.errors)


class KYCDocumentUploadView(APIView, APIResponseMixin):
    """Endpoint pour uploader les documents KYC"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if request.user.kyc_status == 'VERIFIED':
            return self.error_response("KYC déjà vérifié")
        
        serializer = KYCDocumentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    file_obj = serializer.validated_data['file']
                    file_content = file_obj.read()
                    file_hash = hashlib.sha256(file_content).hexdigest()
                    file_obj.seek(0)
                    
                    document, created = KYCDocument.objects.update_or_create(
                        user=request.user,
                        document_type=serializer.validated_data['document_type'],
                        defaults={
                            'file': file_obj,
                            'file_size': file_obj.size,
                            'file_hash': file_hash,
                            'status': 'UPLOADED'
                        }
                    )
                    
                    process_kyc_document.delay(document.id)
                    
                    if request.user.kyc_status == 'PENDING':
                        request.user.kyc_status = 'SUBMITTED'
                        request.user.kyc_submitted_at = timezone.now()
                        request.user.save(update_fields=['kyc_status', 'kyc_submitted_at'])
                    
                    return self.success_response({
                        'document': KYCDocumentSerializer(document).data,
                        'message': 'Document uploadé avec succès. Vérification en cours.'
                    })
                    
            except Exception as e:
                logger.error(f"Erreur upload KYC: {e}")
                return self.error_response("Erreur lors de l'upload du document", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return self.error_response("Document invalide", errors=serializer.errors)


class KYCDocumentListView(generics.ListAPIView):
    """Liste des documents KYC de l'utilisateur"""
    serializer_class = KYCDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return KYCDocument.objects.filter(user=self.request.user)


class KYCStatusView(APIView, APIResponseMixin):
    """Endpoint pour obtenir le statut KYC"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        documents = KYCDocument.objects.filter(user=user)
        
        response_data = {
            'kyc_status': user.kyc_status,
            'kyc_submitted_at': user.kyc_submitted_at,
            'kyc_verified_at': user.kyc_verified_at,
            'kyc_rejection_reason': user.kyc_rejection_reason,
            'documents': KYCDocumentSerializer(documents, many=True).data,
            'required_documents': ['ID_FRONT', 'ID_BACK', 'SELFIE', 'PROOF_OF_ADDRESS'],
            'uploaded_documents': list(documents.values_list('document_type', flat=True))
        }
        
        return self.success_response(response_data)


@method_decorator(csrf_exempt, name='dispatch')
class SmileIDWebhookView(APIView, APIResponseMixin):
    """Webhook pour recevoir les résultats de Smile ID"""
    permission_classes = []
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            result = smile_id_service.parse_webhook_result(data)
            
            # Traiter le résultat
            if result.get('job_id'):
                try:
                    document = KYCDocument.objects.get(smile_id_job_id=result['job_id'])
                    
                    if result.get('job_success'):
                        document.status = 'VERIFIED'
                        document.confidence_score = result.get('confidence', 0)
                        document.verification_notes = "Vérifié avec succès par Smile ID"
                    else:
                        document.status = 'REJECTED'
                        document.verification_notes = f"Rejeté par Smile ID: {result.get('code', 'Raison inconnue')}"
                    
                    document.smile_id_result = result
                    document.save()
                    
                    # Vérifier le statut KYC global
                    from .tasks import check_overall_kyc_status
                    check_overall_kyc_status.delay(document.user.id)
                    
                except KYCDocument.DoesNotExist:
                    logger.error(f"Document non trouvé pour job_id: {result.get('job_id')}")
            
            return Response({'status': 'success'}, status=200)
            
        except Exception as e:
            logger.error(f"Erreur webhook Smile ID: {e}")
            return Response({'status': 'error'}, status=400)


class UserLogoutView(APIView, APIResponseMixin):
    """Endpoint de déconnexion"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return self.success_response({'message': 'Déconnexion réussie'})
        except Exception as e:
            logger.error(f"Erreur déconnexion: {e}")
            return self.success_response({'message': 'Déconnexion réussie'})


# Vues d'administration
class AdminUserListView(generics.ListCreateAPIView):
    """Liste et création d'utilisateurs (admin uniquement)"""
    queryset = CustomUser.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filterset_fields = ['role', 'kyc_status', 'is_active']
    search_fields = ['phone_number', 'first_name', 'last_name', 'email']
    ordering = ['-created_at']


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail d'un utilisateur (admin uniquement)"""
    queryset = CustomUser.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class AdminKYCApprovalView(APIView, APIResponseMixin):
    """Endpoint d'approbation/rejet KYC (admin uniquement)"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return self.error_response("Utilisateur non trouvé", status_code=404)
        
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        
        if action == 'approve':
            user.kyc_status = 'VERIFIED'
            user.kyc_verified_at = timezone.now()
            user.kyc_rejection_reason = ''
            message = f"KYC approuvé pour {user.get_full_name()}"
            
        elif action == 'reject':
            user.kyc_status = 'REJECTED'
            user.kyc_rejection_reason = reason
            message = f"KYC rejeté pour {user.get_full_name()}"
            
        else:
            return self.error_response("Action invalide. Utilisez 'approve' ou 'reject'")
        
        user.save(update_fields=['kyc_status', 'kyc_verified_at', 'kyc_rejection_reason'])
        
        if user.email:
            send_notification_email(
                user.email,
                f"Statut KYC - {message}",
                f"Votre vérification KYC a été {'approuvée' if action == 'approve' else 'rejetée'}. {reason}"
            )
        
        return self.success_response({
            'message': message,
            'user': AdminUserSerializer(user).data
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def user_statistics(request):
    """Statistiques des utilisateurs (admin uniquement)"""
    from django.db.models import Count
    from datetime import timedelta
    
    now = timezone.now()
    last_month = now - timedelta(days=30)
    
    stats = {
        'total_users': CustomUser.objects.count(),
        'new_users_this_month': CustomUser.objects.filter(created_at__gte=last_month).count(),
        'verified_users': CustomUser.objects.filter(kyc_status='VERIFIED').count(),
        'active_users': CustomUser.objects.filter(last_activity__gte=last_month).count(),
        'users_by_role': dict(CustomUser.objects.values('role').annotate(count=Count('role')).values_list('role', 'count')),
        'users_by_kyc_status': dict(CustomUser.objects.values('kyc_status').annotate(count=Count('kyc_status')).values_list('kyc_status', 'count')),
        'failed_login_attempts_today': LoginAttempt.objects.filter(attempted_at__date=now.date(), success=False).count(),
    }
    
    return Response({'success': True, 'data': stats, 'timestamp': now.isoformat()})


class PasswordResetRequestView(APIView, APIResponseMixin):
    """Endpoint de demande de réinitialisation de mot de passe"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Demande de réinitialisation de mot de passe",
        operation_description="""
        Demande de réinitialisation de mot de passe par email.
        
        **Processus:**
        1. Validation de l'email
        2. Génération d'un code de réinitialisation
        3. Envoi du code par email
        4. Stockage du code avec expiration
        
        **Note:** Le code expire après 15 minutes.
        """,
        request_body=PasswordResetRequestSerializer,
        responses={
            200: openapi.Response(
                description="Code de réinitialisation envoyé avec succès",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Code de réinitialisation envoyé à votre email.",
                        "data": {
                            "email": "user@example.com",
                            "expires_at": "2025-08-12T08:00:00Z"
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            ),
            400: openapi.Response(
                description="Email invalide ou non trouvé",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Aucun compte associé à cette adresse email.",
                        "errors": {
                            "email": ["Aucun compte associé à cette adresse email."]
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                user = CustomUser.objects.get(email=email)
                
                # Générer et envoyer le code de réinitialisation
                reset_code = user.generate_password_reset_token()
                
                # Envoyer l'email avec le code
                if user.email:
                    send_notification_email(
                        user.email,
                        "Réinitialisation de mot de passe - Kimi Escrow",
                        f"""
                        Bonjour {user.get_full_name()},
                        
                        Vous avez demandé la réinitialisation de votre mot de passe.
                        Votre code de réinitialisation est : {reset_code}
                        
                        Ce code expire dans 15 minutes.
                        Si vous n'avez pas fait cette demande, ignorez cet email.
                        
                        Cordialement,
                        L'équipe Kimi Escrow
                        """
                    )
                
                return self.success_response({
                    'message': 'Code de réinitialisation envoyé à votre email.',
                    'data': {
                        'email': email,
                        'expires_at': user.password_reset_expires_at.isoformat() if user.password_reset_expires_at else None
                    }
                })
                
            except CustomUser.DoesNotExist:
                return self.error_response("Aucun compte associé à cette adresse email.", status_code=400)
            except Exception as e:
                logger.error(f"Erreur réinitialisation mot de passe: {e}")
                return self.error_response("Erreur lors de l'envoi du code de réinitialisation", status_code=500)
        
        return self.error_response("Données invalides", errors=serializer.errors, status_code=400)


class PasswordResetConfirmView(APIView, APIResponseMixin):
    """Endpoint de confirmation de réinitialisation de mot de passe"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Confirmation de réinitialisation de mot de passe",
        operation_description="""
        Confirmation de réinitialisation de mot de passe avec le code reçu.
        
        **Processus:**
        1. Validation du code de réinitialisation
        2. Vérification de l'expiration
        3. Mise à jour du mot de passe
        4. Invalidation du code utilisé
        
        **Note:** Le code doit être utilisé dans les 15 minutes.
        """,
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: openapi.Response(
                description="Mot de passe mis à jour avec succès",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Votre mot de passe a été mis à jour avec succès.",
                        "data": {
                            "email": "user@example.com",
                            "updated_at": "2025-08-12T07:30:00Z"
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            ),
            400: openapi.Response(
                description="Code invalide ou expiré",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Code de réinitialisation invalide ou expiré.",
                        "errors": {
                            "reset_code": ["Code de réinitialisation invalide ou expiré."]
                        },
                        "timestamp": "2025-08-12T07:30:00Z"
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                reset_code = serializer.validated_data['reset_code']
                new_password = serializer.validated_data['new_password']
                
                user = CustomUser.objects.get(email=email)
                
                # Vérifier le code de réinitialisation
                if not user.verify_password_reset_token(reset_code):
                    return self.error_response("Code de réinitialisation invalide ou expiré", status_code=400)
                
                # Mettre à jour le mot de passe
                user.set_password(new_password)
                user.password_reset_token = None
                user.password_reset_expires_at = None
                user.save(update_fields=['password', 'password_reset_token', 'password_reset_expires_at'])
                
                # Envoyer un email de confirmation
                if user.email:
                    send_notification_email(
                        user.email,
                        "Mot de passe mis à jour - Kimi Escrow",
                        f"""
                        Bonjour {user.get_full_name()},
                        
                        Votre mot de passe a été mis à jour avec succès.
                        Si vous n'avez pas fait cette modification, contactez-nous immédiatement.
                        
                        Cordialement,
                        L'équipe Kimi Escrow
                        """
                    )
                
                return self.success_response({
                    'message': 'Votre mot de passe a été mis à jour avec succès.',
                    'data': {
                        'email': email,
                        'updated_at': timezone.now().isoformat()
                    }
                })
                
            except CustomUser.DoesNotExist:
                return self.error_response("Aucun compte associé à cette adresse email", status_code=400)
            except Exception as e:
                logger.error(f"Erreur confirmation réinitialisation: {e}")
                return self.error_response("Erreur lors de la mise à jour du mot de passe", status_code=500)
        
        return self.error_response("Données invalides", errors=serializer.errors, status_code=400)