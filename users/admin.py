from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, KYCDocument, UserProfile, UserSession, LoginAttempt


class KYCDocumentInline(admin.TabularInline):
    model = KYCDocument
    extra = 0
    readonly_fields = ('status', 'confidence_score', 'verification_notes', 'created_at')
    fields = ('document_type', 'file', 'status', 'confidence_score', 'verification_notes', 'created_at')


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, KYCDocumentInline)
    
    # Champs à afficher dans la liste
    list_display = ('phone_number', 'first_name', 'last_name', 'role', 'kyc_status', 'is_phone_verified', 'is_active', 'created_at')
    list_filter = ('role', 'kyc_status', 'is_phone_verified', 'is_active', 'created_at')
    search_fields = ('phone_number', 'first_name', 'last_name', 'email')
    ordering = ('-created_at',)
    
    # Champs dans le formulaire de détail
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email', 'date_of_birth')
        }),
        ('Rôle et statut', {
            'fields': ('role', 'kyc_status', 'is_phone_verified', 'kyc_rejection_reason')
        }),
        ('Adresse', {
            'fields': ('address_street', 'address_city', 'address_region', 'address_country'),
            'classes': ('collapse',)
        }),
        ('Informations d\'identité', {
            'fields': ('id_card_type', 'id_card_number'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Sécurité', {
            'fields': ('mfa_enabled', 'last_login', 'last_activity'),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('created_at', 'updated_at', 'kyc_submitted_at', 'kyc_verified_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Champs pour l'ajout d'utilisateur
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'last_activity', 
                      'kyc_submitted_at', 'kyc_verified_at')
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Les non-superusers ne peuvent pas modifier certains champs critiques
        if not request.user.is_superuser:
            readonly_fields.extend(['role', 'is_superuser', 'user_permissions'])
        
        return readonly_fields


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'confidence_score', 'created_at')
    list_filter = ('document_type', 'status', 'created_at')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name')
    readonly_fields = ('file_hash', 'file_size', 'smile_id_job_id', 'smile_id_result', 
                      'confidence_score', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'document_type', 'file', 'status')
        }),
        ('Résultats de vérification', {
            'fields': ('confidence_score', 'verification_notes'),
        }),
        ('Métadonnées', {
            'fields': ('file_size', 'file_hash', 'smile_id_job_id'),
            'classes': ('collapse',)
        }),
        ('Résultats Smile ID', {
            'fields': ('smile_id_result',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Une fois que le document a été traité, on ne peut plus le modifier
        if obj and obj.status in ['VERIFIED', 'REJECTED']:
            readonly_fields.extend(['user', 'document_type', 'file'])
        
        return readonly_fields


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_transactions', 'successful_transactions', 'rating_avg', 'email_verified')
    list_filter = ('email_verified', 'bank_account_verified', 'email_notifications', 'sms_notifications')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name', 'occupation', 'company_name')
    readonly_fields = ('total_transactions', 'successful_transactions', 'total_volume', 
                      'rating_avg', 'rating_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user', 'avatar')
        }),
        ('Informations professionnelles', {
            'fields': ('occupation', 'company_name'),
        }),
        ('Préférences de notification', {
            'fields': ('email_notifications', 'sms_notifications', 'push_notifications'),
        }),
        ('Préférences d\'escrow', {
            'fields': ('default_auto_release_days', 'require_confirmation_for_release'),
        }),
        ('Statistiques', {
            'fields': ('total_transactions', 'successful_transactions', 'total_volume', 
                      'rating_avg', 'rating_count'),
            'classes': ('collapse',)
        }),
        ('Vérifications', {
            'fields': ('email_verified', 'bank_account_verified'),
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_info', 'ip_address', 'is_active', 'created_at', 'last_activity')
    list_filter = ('is_active', 'created_at', 'last_activity')
    search_fields = ('user__phone_number', 'device_info', 'ip_address')
    readonly_fields = ('session_token', 'created_at', 'last_activity')
    date_hierarchy = 'created_at'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Modification d'une session existante
            return self.readonly_fields + ('user',)
        return self.readonly_fields


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'ip_address', 'success', 'failure_reason', 'attempted_at')
    list_filter = ('success', 'attempted_at')
    search_fields = ('phone_number', 'ip_address')
    readonly_fields = ('phone_number', 'ip_address', 'user_agent', 'success', 
                      'failure_reason', 'attempted_at')
    date_hierarchy = 'attempted_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Personnalisation de l'interface d'administration
admin.site.site_header = "Administration Kimi Escrow"
admin.site.site_title = "Kimi Escrow Admin"
admin.site.index_title = "Tableau de bord administrateur"