from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    EscrowTransaction, Milestone, Proof, TransactionMessage, TransactionRating,
    FaceToFaceDetails, InternationalDetails
)
from core.utils import is_amount_valid

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple pour les utilisateurs dans les transactions"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'full_name']
        read_only_fields = fields


class MilestoneSerializer(serializers.ModelSerializer):
    """Serializer pour les jalons"""
    can_be_completed = serializers.SerializerMethodField()
    can_be_approved = serializers.SerializerMethodField()
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Milestone
        fields = [
            'id', 'title', 'description', 'amount', 'percentage', 'order',
            'status', 'due_date', 'completed_at', 'approved_at',
            'completed_by', 'completed_by_name', 'approved_by', 'approved_by_name',
            'completion_notes', 'approval_notes', 'created_at', 'updated_at',
            'can_be_completed', 'can_be_approved'
        ]
        read_only_fields = [
            'id', 'completed_at', 'approved_at', 'completed_by', 'approved_by',
            'created_at', 'updated_at', 'can_be_completed', 'can_be_approved'
        ]
    
    def get_can_be_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_be_completed(request.user)
        return False
    
    def get_can_be_approved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_be_approved(request.user)
        return False


class FaceToFaceDetailsSerializer(serializers.ModelSerializer):
    """Serializer pour les détails face-à-face"""
    meeting_location_display = serializers.SerializerMethodField()
    auto_validation_deadline_display = serializers.SerializerMethodField()
    
    class Meta:
        model = FaceToFaceDetails
        fields = [
            'id', 'meeting_location', 'meeting_latitude', 'meeting_longitude',
            'meeting_address', 'meeting_date', 'meeting_duration',
            'auto_validation_hours', 'auto_validation_deadline', 'auto_validation_deadline_display',
            'initial_proof', 'final_proof', 'meeting_status', 'meeting_notes',
            'metadata', 'created_at', 'updated_at', 'meeting_location_display'
        ]
        read_only_fields = [
            'id', 'auto_validation_deadline', 'created_at', 'updated_at',
            'meeting_location_display', 'auto_validation_deadline_display'
        ]
    
    def get_meeting_location_display(self, obj):
        if obj.meeting_latitude and obj.meeting_longitude:
            return f"{obj.meeting_latitude}, {obj.meeting_longitude}"
        return obj.meeting_location
    
    def get_auto_validation_deadline_display(self, obj):
        if obj.auto_validation_deadline:
            return obj.auto_validation_deadline.strftime("%d/%m/%Y %H:%M")
        return None


class InternationalDetailsSerializer(serializers.ModelSerializer):
    """Serializer pour les détails internationaux"""
    buyer_currency_display = serializers.CharField(source='get_buyer_currency_display', read_only=True)
    seller_currency_display = serializers.CharField(source='get_seller_currency_display', read_only=True)
    carrier_name_display = serializers.CharField(source='get_carrier_name_display', read_only=True)
    inspection_deadline_display = serializers.SerializerMethodField()
    
    class Meta:
        model = InternationalDetails
        fields = [
            'id', 'buyer_currency', 'buyer_currency_display', 'seller_currency', 'seller_currency_display',
            'exchange_rate', 'exchange_rate_fixed', 'exchange_rate_date',
            'invoice_number', 'certificate_number', 'bill_of_lading',
            'carrier_name', 'carrier_name_display', 'tracking_number', 'tracking_url',
            'inspection_days', 'inspection_deadline', 'inspection_deadline_display',
            'metadata', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'inspection_deadline', 'created_at', 'updated_at',
            'buyer_currency_display', 'seller_currency_display', 'carrier_name_display',
            'inspection_deadline_display'
        ]
    
    def get_inspection_deadline_display(self, obj):
        if obj.inspection_deadline:
            return obj.inspection_deadline.strftime("%d/%m/%Y %H:%M")
        return None


class ProofSerializer(serializers.ModelSerializer):
    """Serializer pour les preuves avec géolocalisation"""
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    has_location = serializers.BooleanField(source='has_location', read_only=True)
    
    class Meta:
        model = Proof
        fields = [
            'id', 'proof_type', 'title', 'description', 'file', 'file_url',
            'text_content', 'latitude', 'longitude', 'location_address', 'location_accuracy',
            'location_display', 'has_location', 'metadata', 'submitted_by', 'submitted_by_name',
            'is_verified', 'verified_at', 'verified_by', 'verified_by_name',
            'verification_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'submitted_by', 'submitted_by_name', 'is_verified',
            'verified_at', 'verified_by', 'verified_by_name', 'verification_notes',
            'created_at', 'updated_at', 'file_url', 'location_display', 'has_location'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class TransactionMessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages de transaction"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    attachment_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TransactionMessage
        fields = [
            'id', 'sender', 'sender_name', 'message', 'is_system_message',
            'attachment', 'attachment_url', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'sender', 'sender_name', 'is_system_message', 'is_read',
            'read_at', 'created_at', 'attachment_url'
        ]
    
    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
        return None


class TransactionRatingSerializer(serializers.ModelSerializer):
    """Serializer pour les évaluations"""
    rater_name = serializers.CharField(source='rater.get_full_name', read_only=True)
    rated_user_name = serializers.CharField(source='rated_user.get_full_name', read_only=True)
    
    class Meta:
        model = TransactionRating
        fields = [
            'id', 'rater', 'rater_name', 'rated_user', 'rated_user_name',
            'rating', 'comment', 'communication_rating', 'delivery_rating',
            'quality_rating', 'would_recommend', 'created_at'
        ]
        read_only_fields = ['id', 'rater', 'rater_name', 'rated_user_name', 'created_at']
    
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("La note doit être comprise entre 1 et 5.")
        return value


class EscrowTransactionListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des transactions (vue simplifiée)"""
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = EscrowTransaction
        fields = [
            'id', 'transaction_id', 'title', 'category', 'category_display',
            'amount', 'commission', 'total_amount', 'status', 'status_display',
            'buyer', 'buyer_name', 'seller', 'seller_name', 'user_role',
            'payment_deadline', 'delivery_deadline', 'auto_release_date',
            'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_participant_role(request.user)
        return None


class EscrowTransactionDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une transaction avec tous les détails"""
    buyer = UserSimpleSerializer(read_only=True)
    seller = UserSimpleSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    
    # Relations
    milestones = MilestoneSerializer(many=True, read_only=True)
    proofs = ProofSerializer(many=True, read_only=True)
    messages = TransactionMessageSerializer(many=True, read_only=True)
    ratings = TransactionRatingSerializer(many=True, read_only=True)
    
    # Détails spécifiques selon le type
    face_to_face_details = FaceToFaceDetailsSerializer(read_only=True)
    international_details = InternationalDetailsSerializer(read_only=True)
    
    # Permissions et statuts
    user_role = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_mark_delivered = serializers.SerializerMethodField()
    can_confirm_delivery = serializers.SerializerMethodField()
    can_create_dispute = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    should_auto_release = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = EscrowTransaction
        fields = [
            'id', 'transaction_id', 'title', 'description', 'category', 'category_display',
            'transaction_type', 'transaction_type_display', 'currency', 'currency_display',
            'amount', 'commission', 'total_amount', 'status', 'status_display',
            'buyer', 'seller', 'user_role',
            'payment_deadline', 'delivery_deadline', 'auto_release_date', 'dispute_deadline',
            'funds_received_at', 'delivered_at', 'released_at', 'cancelled_at',
            'auto_release_enabled', 'auto_release_days', 'require_delivery_confirmation',
            'delivery_address', 'delivery_method', 'tracking_info',
            'metadata', 'notes', 'created_at', 'updated_at',
            'milestones', 'proofs', 'messages', 'ratings',
            'face_to_face_details', 'international_details',
            'can_cancel', 'can_mark_delivered', 'can_confirm_delivery', 'can_create_dispute',
            'is_overdue', 'should_auto_release'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'commission', 'total_amount', 'status',
            'buyer', 'seller', 'funds_received_at', 'delivered_at', 'released_at',
            'cancelled_at', 'created_at', 'updated_at', 'milestones', 'proofs',
            'messages', 'ratings', 'face_to_face_details', 'international_details',
            'user_role', 'can_cancel', 'can_mark_delivered', 'can_confirm_delivery',
            'can_create_dispute', 'is_overdue', 'should_auto_release'
        ]
    
    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_participant_role(request.user)
        return None
    
    def get_can_cancel(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_be_cancelled(request.user)
        return False
    
    def get_can_mark_delivered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_mark_delivered(request.user)
        return False
    
    def get_can_confirm_delivery(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_confirm_delivery(request.user)
        return False
    
    def get_can_create_dispute(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_create_dispute(request.user)
        return False


class EscrowTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création d'une transaction avec support des nouveaux types"""
    seller_phone = serializers.CharField(write_only=True, help_text="Numéro de téléphone du vendeur")
    transaction_type = serializers.ChoiceField(choices=EscrowTransaction.TRANSACTION_TYPE_CHOICES, default='STANDARD')
    currency = serializers.ChoiceField(choices=EscrowTransaction.CURRENCY_CHOICES, default='XAF')
    
    # Données pour face-à-face
    face_to_face_data = serializers.DictField(required=False, help_text="Données pour transaction face-à-face")
    
    # Données pour international
    international_data = serializers.DictField(required=False, help_text="Données pour transaction internationale")
    
    # Jalons (pour transactions standard et par jalons)
    milestones_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="Liste des jalons (optionnel)"
    )
    
    class Meta:
        model = EscrowTransaction
        fields = [
            'title', 'description', 'category', 'amount', 'transaction_type', 'currency',
            'payment_deadline', 'delivery_deadline',
            'auto_release_enabled', 'auto_release_days', 'require_delivery_confirmation',
            'delivery_address', 'delivery_method', 'notes',
            'seller_phone', 'milestones_data', 'face_to_face_data', 'international_data'
        ]
    
    def validate_amount(self, value):
        if not is_amount_valid(value):
            from django.conf import settings
            min_amount = getattr(settings, 'MINIMUM_ESCROW_AMOUNT', 1000)
            max_amount = getattr(settings, 'MAXIMUM_ESCROW_AMOUNT', 10000000)
            raise serializers.ValidationError(
                f"Le montant doit être compris entre {min_amount} et {max_amount} XAF."
            )
        return value
    
    def validate_seller_phone(self, value):
        from core.utils import sanitize_phone_number, validate_cameroon_phone
        
        normalized_phone = sanitize_phone_number(value)
        if not validate_cameroon_phone(normalized_phone):
            raise serializers.ValidationError("Format de numéro de téléphone invalide.")
        
        try:
            seller = User.objects.get(phone_number=normalized_phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("Aucun utilisateur trouvé avec ce numéro.")
        
        if not seller.can_create_escrow():
            raise serializers.ValidationError("Ce vendeur ne peut pas participer aux transactions escrow.")
        
        return normalized_phone
    
    def validate(self, attrs):
        # Validation de base
        if attrs['payment_deadline'] <= timezone.now():
            raise serializers.ValidationError(
                {"payment_deadline": "La date limite de paiement doit être dans le futur."}
            )
        
        if attrs['delivery_deadline'] <= attrs['payment_deadline']:
            raise serializers.ValidationError(
                {"delivery_deadline": "La date limite de livraison doit être après la date limite de paiement."}
            )
        
        # Vérifier que l'acheteur et le vendeur sont différents
        seller_phone = attrs.get('seller_phone')
        request = self.context.get('request')
        if request and request.user.phone_number == seller_phone:
            raise serializers.ValidationError(
                {"seller_phone": "Vous ne pouvez pas créer une transaction avec vous-même."}
            )
        
        # Validation spécifique selon le type de transaction
        transaction_type = attrs.get('transaction_type', 'STANDARD')
        
        if transaction_type == 'FACE_TO_FACE':
            face_to_face_data = attrs.get('face_to_face_data', {})
            if not face_to_face_data.get('meeting_location'):
                raise serializers.ValidationError(
                    {"face_to_face_data": "Le lieu de rencontre est obligatoire pour les transactions face-à-face."}
                )
            if not face_to_face_data.get('meeting_date'):
                raise serializers.ValidationError(
                    {"face_to_face_data": "La date de rencontre est obligatoire pour les transactions face-à-face."}
                )
        
        elif transaction_type == 'INTERNATIONAL':
            international_data = attrs.get('international_data', {})
            if not international_data.get('buyer_currency'):
                raise serializers.ValidationError(
                    {"international_data": "La devise de l'acheteur est obligatoire pour les transactions internationales."}
                )
            if not international_data.get('seller_currency'):
                raise serializers.ValidationError(
                    {"international_data": "La devise du vendeur est obligatoire pour les transactions internationales."}
                )
        
        elif transaction_type == 'MILESTONE':
            milestones_data = attrs.get('milestones_data', [])
            if not milestones_data:
                raise serializers.ValidationError(
                    {"milestones_data": "Les jalons sont obligatoires pour les transactions par jalons."}
                )
            total_percentage = sum(float(m.get('percentage', 0)) for m in milestones_data)
            if abs(total_percentage - 100.0) > 0.01:
                raise serializers.ValidationError(
                    {"milestones_data": "La somme des pourcentages des jalons doit être égale à 100%."}
                )
        
        return attrs
    
    def create(self, validated_data):
        # Extraire les données spécifiques
        seller_phone = validated_data.pop('seller_phone')
        face_to_face_data = validated_data.pop('face_to_face_data', {})
        international_data = validated_data.pop('international_data', {})
        milestones_data = validated_data.pop('milestones_data', [])
        
        # Obtenir le vendeur
        seller = User.objects.get(phone_number=seller_phone)
        
        # Créer la transaction
        transaction = EscrowTransaction.objects.create(
            buyer=self.context['request'].user,
            seller=seller,
            **validated_data
        )
        
        # Créer les détails spécifiques selon le type
        if transaction.transaction_type == 'FACE_TO_FACE':
            from django.utils.dateparse import parse_datetime
            # Assurer que meeting_date est un objet datetime
            if 'meeting_date' in face_to_face_data and isinstance(face_to_face_data['meeting_date'], str):
                face_to_face_data['meeting_date'] = parse_datetime(face_to_face_data['meeting_date'])
            
            FaceToFaceDetails.objects.create(
                transaction=transaction,
                **face_to_face_data
            )
        
        elif transaction.transaction_type == 'INTERNATIONAL':
            InternationalDetails.objects.create(
                transaction=transaction,
                **international_data
            )
        
        # Créer les jalons si fournis
        for order, milestone_data in enumerate(milestones_data, 1):
            Milestone.objects.create(
                transaction=transaction,
                order=order,
                title=milestone_data['title'],
                description=milestone_data.get('description', ''),
                percentage=milestone_data['percentage'],
                amount=transaction.amount * milestone_data['percentage'] / 100,
                due_date=milestone_data.get('due_date')
            )
        
        return transaction


class TransactionActionSerializer(serializers.Serializer):
    """Serializer pour les actions sur les transactions"""
    action = serializers.ChoiceField(choices=[
        'cancel', 'mark_delivered', 'confirm_delivery', 'request_release'
    ])
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        action = attrs['action']
        transaction = self.context['transaction']
        user = self.context['request'].user
        
        if action == 'cancel' and not transaction.can_be_cancelled(user):
            raise serializers.ValidationError("Vous ne pouvez pas annuler cette transaction.")
        
        if action == 'mark_delivered' and not transaction.can_mark_delivered(user):
            raise serializers.ValidationError("Vous ne pouvez pas marquer cette transaction comme livrée.")
        
        if action == 'confirm_delivery' and not transaction.can_confirm_delivery(user):
            raise serializers.ValidationError("Vous ne pouvez pas confirmer la livraison de cette transaction.")
        
        return attrs


class MilestoneActionSerializer(serializers.Serializer):
    """Serializer pour les actions sur les jalons"""
    action = serializers.ChoiceField(choices=['complete', 'approve', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        action = attrs['action']
        milestone = self.context['milestone']
        user = self.context['request'].user
        
        if action == 'complete' and not milestone.can_be_completed(user):
            raise serializers.ValidationError("Vous ne pouvez pas marquer ce jalon comme terminé.")
        
        if action in ['approve', 'reject'] and not milestone.can_be_approved(user):
            raise serializers.ValidationError("Vous ne pouvez pas approuver/rejeter ce jalon.")
        
        return attrs
