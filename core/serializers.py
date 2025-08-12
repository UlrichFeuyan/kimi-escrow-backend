from rest_framework import serializers
from .models import AuditLog, GlobalSettings


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_name', 'action', 'resource_type', 
                 'resource_id', 'details', 'ip_address', 'timestamp']
        read_only_fields = fields
    
    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.phone_number
        return "Système"


class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = ['id', 'key', 'value', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
