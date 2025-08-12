from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import EscrowTransaction, Milestone, Proof, TransactionMessage, TransactionRating
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


class ProofSerializer(serializers.ModelSerializer):
    """Serializer pour les preuves"""
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Proof
        fields = [
            'id', 'proof_type', 'title', 'description', 'file', 'file_url',
            'text_content', 'metadata', 'submitted_by', 'submitted_by_name',
            'is_verified', 'verified_at', 'verified_by', 'verified_by_name',
            'verification_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'submitted_by', 'submitted_by_name', 'is_verified',
            'verified_at', 'verified_by', 'verified_by_name', 'verification_notes',
            'created_at', 'updated_at', 'file_url'
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
    """Serializer détaillé pour une transaction"""
    buyer = UserSimpleSerializer(read_only=True)
    seller = UserSimpleSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    # Relations
    milestones = MilestoneSerializer(many=True, read_only=True)
    proofs = ProofSerializer(many=True, read_only=True)
    messages = TransactionMessageSerializer(many=True, read_only=True)
    ratings = TransactionRatingSerializer(many=True, read_only=True)
    
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
            'amount', 'commission', 'total_amount', 'status', 'status_display',
            'buyer', 'seller', 'user_role',
            'payment_deadline', 'delivery_deadline', 'auto_release_date', 'dispute_deadline',
            'funds_received_at', 'delivered_at', 'released_at', 'cancelled_at',
            'auto_release_enabled', 'auto_release_days', 'require_delivery_confirmation',
            'delivery_address', 'delivery_method', 'tracking_info',
            'metadata', 'notes', 'created_at', 'updated_at',
            'milestones', 'proofs', 'messages', 'ratings',
            'can_cancel', 'can_mark_delivered', 'can_confirm_delivery', 'can_create_dispute',
            'is_overdue', 'should_auto_release'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'commission', 'total_amount', 'status',
            'buyer', 'seller', 'funds_received_at', 'delivered_at', 'released_at',
            'cancelled_at', 'created_at', 'updated_at', 'milestones', 'proofs',
            'messages', 'ratings', 'user_role', 'can_cancel', 'can_mark_delivered',
            'can_confirm_delivery', 'can_create_dispute', 'is_overdue', 'should_auto_release'
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
    """Serializer pour la création d'une transaction"""
    seller_phone = serializers.CharField(write_only=True, help_text="Numéro de téléphone du vendeur")
    milestones_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="Liste des jalons (optionnel)"
    )
    
    class Meta:
        model = EscrowTransaction
        fields = [
            'title', 'description', 'category', 'amount',
            'payment_deadline', 'delivery_deadline',
            'auto_release_enabled', 'auto_release_days', 'require_delivery_confirmation',
            'delivery_address', 'delivery_method', 'notes',
            'seller_phone', 'milestones_data'
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
        # Vérifier les dates
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
        
        # Valider les jalons si fournis
        milestones_data = attrs.get('milestones_data', [])
        if milestones_data:
            total_percentage = sum(float(m.get('percentage', 0)) for m in milestones_data)
            if abs(total_percentage - 100.0) > 0.01:  # Tolérance pour les erreurs de floating point
                raise serializers.ValidationError(
                    {"milestones_data": "La somme des pourcentages des jalons doit être égale à 100%."}
                )
        
        return attrs
    
    def create(self, validated_data):
        # Extraire les données des jalons
        milestones_data = validated_data.pop('milestones_data', [])
        seller_phone = validated_data.pop('seller_phone')
        
        # Obtenir le vendeur
        seller = User.objects.get(phone_number=seller_phone)
        
        # Créer la transaction
        transaction = EscrowTransaction.objects.create(
            buyer=self.context['request'].user,
            seller=seller,
            **validated_data
        )
        
        # Créer les jalons
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
