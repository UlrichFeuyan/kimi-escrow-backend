from rest_framework import serializers
from .models import Payment, PaymentMethod, Webhook, EscrowAccount


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer pour les méthodes de paiement"""
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'provider', 'status', 'supports_collection',
            'supports_disbursement', 'min_amount', 'max_amount',
            'transaction_fee', 'logo', 'description'
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer pour les paiements"""
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'reference', 'external_reference', 'payment_type', 'type_display',
            'amount', 'fee', 'total_amount', 'currency', 'status', 'status_display',
            'payment_method', 'payment_method_name', 'phone_number', 'email',
            'description', 'expires_at', 'processed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reference', 'external_reference', 'fee', 'total_amount',
            'status', 'expires_at', 'processed_at', 'created_at', 'updated_at'
        ]


class WebhookSerializer(serializers.ModelSerializer):
    """Serializer pour les webhooks"""
    class Meta:
        model = Webhook
        fields = [
            'id', 'webhook_id', 'source', 'event_type', 'status',
            'processing_attempts', 'processed_at', 'created_at'
        ]
        read_only_fields = fields


class EscrowAccountSerializer(serializers.ModelSerializer):
    """Serializer pour les comptes séquestres"""
    available_balance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    transaction_id = serializers.CharField(source='transaction.transaction_id', read_only=True)
    
    class Meta:
        model = EscrowAccount
        fields = [
            'id', 'account_number', 'transaction_id', 'balance',
            'frozen_amount', 'available_balance', 'status',
            'opened_at', 'closed_at'
        ]
        read_only_fields = fields

