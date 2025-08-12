from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Dispute, DisputeEvidence, DisputeComment, DisputeResolution

User = get_user_model()


class DisputeSerializer(serializers.ModelSerializer):
    """Serializer pour les litiges"""
    complainant_name = serializers.CharField(source='complainant.get_full_name', read_only=True)
    respondent_name = serializers.CharField(source='respondent.get_full_name', read_only=True)
    arbitre_name = serializers.CharField(source='arbitre.get_full_name', read_only=True)
    transaction_id = serializers.CharField(source='transaction.transaction_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Dispute
        fields = [
            'id', 'dispute_id', 'transaction', 'transaction_id',
            'complainant', 'complainant_name', 'respondent', 'respondent_name',
            'arbitre', 'arbitre_name', 'category', 'category_display',
            'title', 'description', 'evidence_description',
            'status', 'status_display', 'verdict', 'resolution_notes',
            'refund_amount', 'priority', 'assigned_at', 'review_started_at',
            'resolved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'dispute_id', 'complainant', 'respondent', 'arbitre',
            'status', 'verdict', 'resolution_notes', 'refund_amount',
            'assigned_at', 'review_started_at', 'resolved_at',
            'created_at', 'updated_at'
        ]


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    """Serializer pour les preuves de litige"""
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DisputeEvidence
        fields = [
            'id', 'evidence_type', 'title', 'description', 'file', 'file_url',
            'file_size', 'submitted_by', 'submitted_by_name', 'created_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'submitted_by', 'submitted_by_name', 'created_at'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class DisputeCommentSerializer(serializers.ModelSerializer):
    """Serializer pour les commentaires de litige"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    attachment_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DisputeComment
        fields = [
            'id', 'author', 'author_name', 'comment', 'is_internal',
            'attachment', 'attachment_url', 'created_at'
        ]
        read_only_fields = [
            'id', 'author', 'author_name', 'created_at'
        ]
    
    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
        return None


class DisputeResolutionSerializer(serializers.ModelSerializer):
    """Serializer pour les résolutions de litige"""
    class Meta:
        model = DisputeResolution
        fields = [
            'id', 'summary', 'reasoning', 'buyer_action', 'seller_action',
            'buyer_penalty', 'seller_penalty', 'complainant_satisfied',
            'respondent_satisfied', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

