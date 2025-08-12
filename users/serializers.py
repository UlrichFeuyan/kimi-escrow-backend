from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import CustomUser, KYCDocument, UserProfile, LoginAttempt
from core.utils import validate_cameroon_phone, sanitize_phone_number


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription des utilisateurs
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirmation = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'phone_number', 'email', 'first_name', 'last_name', 
            'role', 'password', 'password_confirmation', 'preferred_language'
        ]
        extra_kwargs = {
            'email': {'required': False},
            'role': {'default': 'BUYER'}
        }
    
    def validate_phone_number(self, value):
        """Valider et normaliser le numéro de téléphone"""
        if not validate_cameroon_phone(value):
            raise serializers.ValidationError(
                "Format de numéro de téléphone camerounais invalide. Ex: +237612345678"
            )
        return sanitize_phone_number(value)
    
    def validate(self, attrs):
        """Validation croisée"""
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError(
                {"password_confirmation": "Les mots de passe ne correspondent pas."}
            )
        
        # Vérifier si le numéro existe déjà
        phone_number = attrs.get('phone_number')
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                {"phone_number": "Ce numéro de téléphone est déjà utilisé."}
            )
        
        return attrs
    
    def create(self, validated_data):
        """Créer un nouvel utilisateur"""
        validated_data.pop('password_confirmation')
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Générer le token de vérification SMS
        user.generate_phone_verification_token()
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer pour la connexion des utilisateurs
    """
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate_phone_number(self, value):
        """Valider et normaliser le numéro de téléphone"""
        return sanitize_phone_number(value)
    
    def validate(self, attrs):
        """Authentifier l'utilisateur"""
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        
        if phone_number and password:
            user = authenticate(
                request=self.context.get('request'),
                username=phone_number,
                password=password
            )
            
            if not user:
                # Enregistrer la tentative de connexion échouée
                request = self.context.get('request')
                if request:
                    LoginAttempt.objects.create(
                        phone_number=phone_number,
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=False,
                        failure_reason='Invalid credentials'
                    )
                
                raise serializers.ValidationError(
                    "Numéro de téléphone ou mot de passe incorrect."
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    "Ce compte a été désactivé."
                )
            
            # Enregistrer la connexion réussie
            request = self.context.get('request')
            if request:
                LoginAttempt.objects.create(
                    phone_number=phone_number,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=True
                )
                
                # Mettre à jour la dernière activité
                user.last_activity = timezone.now()
                user.save(update_fields=['last_activity'])
            
            attrs['user'] = user
            return attrs
        
        raise serializers.ValidationError(
            "Le numéro de téléphone et le mot de passe sont requis."
        )


class PhoneVerificationSerializer(serializers.Serializer):
    """
    Serializer pour la vérification du numéro de téléphone
    """
    verification_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_verification_code(self, value):
        """Valider le code de vérification"""
        if not value.isdigit():
            raise serializers.ValidationError("Le code doit contenir uniquement des chiffres.")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour le profil utilisateur
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    can_create_escrow = serializers.BooleanField(read_only=True)
    can_arbitrate = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'kyc_status', 'is_phone_verified', 'date_of_birth',
            'address_street', 'address_city', 'address_region', 'address_country',
            'preferred_language', 'can_create_escrow', 'can_arbitrate',
            'created_at', 'updated_at', 'last_activity'
        ]
        read_only_fields = [
            'id', 'phone_number', 'role', 'kyc_status', 'is_phone_verified',
            'can_create_escrow', 'can_arbitrate', 'created_at', 'updated_at', 'last_activity'
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour du profil utilisateur
    """
    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'date_of_birth',
            'address_street', 'address_city', 'address_region',
            'preferred_language'
        ]
    
    def validate_email(self, value):
        """Valider l'unicité de l'email"""
        if value and CustomUser.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Cette adresse email est déjà utilisée.")
        return value


class KYCDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer pour les documents KYC
    """
    class Meta:
        model = KYCDocument
        fields = [
            'id', 'document_type', 'file', 'status', 'confidence_score',
            'verification_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'confidence_score', 'verification_notes',
            'created_at', 'updated_at'
        ]
    
    def validate_file(self, value):
        """Valider le fichier uploadé"""
        # Vérifier la taille du fichier (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Le fichier ne doit pas dépasser 10MB.")
        
        # Vérifier le type de fichier
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Format de fichier non supporté. Utilisez JPEG, PNG ou PDF."
            )
        
        return value


class UserExtendedProfileSerializer(serializers.ModelSerializer):
    """
    Serializer étendu avec informations du profil
    """
    profile = serializers.SerializerMethodField()
    kyc_documents = KYCDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name',
            'role', 'kyc_status', 'is_phone_verified', 'date_of_birth',
            'address_street', 'address_city', 'address_region', 'address_country',
            'preferred_language', 'created_at', 'updated_at', 'last_activity',
            'profile', 'kyc_documents'
        ]
        read_only_fields = fields
    
    def get_profile(self, obj):
        """Obtenir les informations du profil étendu"""
        try:
            profile = obj.profile
            return {
                'avatar': profile.avatar.url if profile.avatar else None,
                'occupation': profile.occupation,
                'company_name': profile.company_name,
                'total_transactions': profile.total_transactions,
                'successful_transactions': profile.successful_transactions,
                'total_volume': profile.total_volume,
                'rating_avg': profile.rating_avg,
                'rating_count': profile.rating_count,
                'email_verified': profile.email_verified,
                'bank_account_verified': profile.bank_account_verified,
            }
        except UserProfile.DoesNotExist:
            return None


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer pour le changement de mot de passe
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirmation = serializers.CharField(write_only=True)
    
    def validate_current_password(self, value):
        """Valider le mot de passe actuel"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value
    
    def validate(self, attrs):
        """Validation croisée"""
        if attrs['new_password'] != attrs['new_password_confirmation']:
            raise serializers.ValidationError(
                {"new_password_confirmation": "Les nouveaux mots de passe ne correspondent pas."}
            )
        return attrs
    
    def save(self, **kwargs):
        """Changer le mot de passe"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer pour les administrateurs (vue complète)
    """
    profile = serializers.SerializerMethodField()
    recent_login_attempts = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name',
            'role', 'kyc_status', 'is_phone_verified', 'is_active',
            'date_of_birth', 'id_card_number', 'id_card_type',
            'address_street', 'address_city', 'address_region', 'address_country',
            'preferred_language', 'mfa_enabled', 'created_at', 'updated_at',
            'last_activity', 'profile', 'recent_login_attempts'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_profile(self, obj):
        """Obtenir les informations du profil"""
        try:
            return UserExtendedProfileSerializer(obj).data['profile']
        except:
            return None
    
    def get_recent_login_attempts(self, obj):
        """Obtenir les tentatives de connexion récentes"""
        attempts = LoginAttempt.objects.filter(
            phone_number=obj.phone_number
        ).order_by('-attempted_at')[:5]
        
        return [{
            'ip_address': attempt.ip_address,
            'success': attempt.success,
            'failure_reason': attempt.failure_reason,
            'attempted_at': attempt.attempted_at,
        } for attempt in attempts]
