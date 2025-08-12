from django.contrib import admin
from .models import AuditLog, GlobalSettings


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'resource_type', 'resource_id', 'timestamp')
    list_filter = ('action', 'resource_type', 'timestamp')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name', 'resource_id')
    readonly_fields = ('user', 'action', 'resource_type', 'resource_id', 'details', 
                      'ip_address', 'user_agent', 'timestamp')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.key in ['ESCROW_COMMISSION_RATE', 'MINIMUM_ESCROW_AMOUNT']:
            # Certains paramètres critiques ne peuvent être modifiés que par les superusers
            if not request.user.is_superuser:
                return self.readonly_fields + ('key', 'value')
        return self.readonly_fields
