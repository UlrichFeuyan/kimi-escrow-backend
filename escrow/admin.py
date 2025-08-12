from django.contrib import admin
from django.utils.html import format_html
from .models import EscrowTransaction, Milestone, Proof, TransactionMessage, TransactionRating


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    readonly_fields = ('completed_at', 'approved_at', 'completed_by', 'approved_by')
    fields = ('order', 'title', 'percentage', 'amount', 'status', 'due_date', 
             'completed_at', 'approved_at')


class ProofInline(admin.TabularInline):
    model = Proof
    extra = 0
    readonly_fields = ('submitted_by', 'is_verified', 'verified_at', 'verified_by')
    fields = ('proof_type', 'title', 'file', 'submitted_by', 'is_verified', 'verified_at')


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    inlines = (MilestoneInline, ProofInline)
    
    list_display = ('transaction_id', 'title', 'buyer', 'seller', 'amount', 'status', 
                   'created_at', 'delivery_deadline')
    list_filter = ('status', 'category', 'auto_release_enabled', 'created_at')
    search_fields = ('transaction_id', 'title', 'buyer__phone_number', 'seller__phone_number',
                    'buyer__first_name', 'buyer__last_name', 'seller__first_name', 'seller__last_name')
    readonly_fields = ('transaction_id', 'commission', 'total_amount', 'funds_received_at',
                      'delivered_at', 'released_at', 'cancelled_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('transaction_id', 'title', 'description', 'category')
        }),
        ('Participants', {
            'fields': ('buyer', 'seller')
        }),
        ('Montants', {
            'fields': ('amount', 'commission', 'total_amount')
        }),
        ('Statut et dates', {
            'fields': ('status', 'payment_deadline', 'delivery_deadline', 'auto_release_date',
                      'dispute_deadline')
        }),
        ('Événements', {
            'fields': ('funds_received_at', 'delivered_at', 'released_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('auto_release_enabled', 'auto_release_days', 'require_delivery_confirmation'),
            'classes': ('collapse',)
        }),
        ('Livraison', {
            'fields': ('delivery_address', 'delivery_method', 'tracking_info'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('metadata', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Une fois que la transaction a commencé, certains champs ne peuvent plus être modifiés
        if obj and obj.status != 'PENDING_FUNDS':
            readonly_fields.extend(['buyer', 'seller', 'amount', 'payment_deadline'])
        
        return readonly_fields


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'order', 'title', 'percentage', 'status', 'due_date')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction__transaction_id', 'title')
    readonly_fields = ('completed_at', 'approved_at', 'completed_by', 'approved_by', 
                      'created_at', 'updated_at')
    
    fieldsets = (
        ('Jalon', {
            'fields': ('transaction', 'order', 'title', 'description')
        }),
        ('Montant et échéance', {
            'fields': ('amount', 'percentage', 'due_date')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Completion', {
            'fields': ('completed_at', 'completed_by', 'completion_notes'),
            'classes': ('collapse',)
        }),
        ('Approbation', {
            'fields': ('approved_at', 'approved_by', 'approval_notes'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'proof_type', 'title', 'submitted_by', 'is_verified', 'created_at')
    list_filter = ('proof_type', 'is_verified', 'created_at')
    search_fields = ('transaction__transaction_id', 'title', 'submitted_by__phone_number')
    readonly_fields = ('submitted_by', 'verified_at', 'verified_by', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Preuve', {
            'fields': ('transaction', 'milestone', 'proof_type', 'title', 'description')
        }),
        ('Contenu', {
            'fields': ('file', 'text_content', 'metadata')
        }),
        ('Soumission', {
            'fields': ('submitted_by', 'created_at')
        }),
        ('Vérification', {
            'fields': ('is_verified', 'verified_at', 'verified_by', 'verification_notes'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransactionMessage)
class TransactionMessageAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'sender', 'message_preview', 'is_system_message', 'is_read', 'created_at')
    list_filter = ('is_system_message', 'is_read', 'created_at')
    search_fields = ('transaction__transaction_id', 'sender__phone_number', 'message')
    readonly_fields = ('sender', 'created_at', 'read_at')
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = "Aperçu du message"


@admin.register(TransactionRating)
class TransactionRatingAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'rater', 'rated_user', 'rating', 'would_recommend', 'created_at')
    list_filter = ('rating', 'would_recommend', 'created_at')
    search_fields = ('transaction__transaction_id', 'rater__phone_number', 'rated_user__phone_number')
    readonly_fields = ('rater', 'rated_user', 'created_at')
    
    fieldsets = (
        ('Évaluation', {
            'fields': ('transaction', 'rater', 'rated_user', 'rating')
        }),
        ('Détails', {
            'fields': ('communication_rating', 'delivery_rating', 'quality_rating', 'would_recommend')
        }),
        ('Commentaire', {
            'fields': ('comment',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )