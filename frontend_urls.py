"""
URLs pour le frontend Django de Kimi Escrow
Version production avec toutes les fonctionnalités
"""

from django.urls import path
from django.views.generic import TemplateView
from django.shortcuts import render
from frontend_views import *

urlpatterns = [
    # ===== PAGES PRINCIPALES ===== #
    path('', home, name='home'),
    
    # ===== AUTHENTIFICATION ===== #
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('verify-phone/', verify_phone, name='verify_phone'),
    
    # ===== PROFIL UTILISATEUR ===== #
    path('profile/', profile_view, name='profile'),
    path('debug-user/', lambda request: render(request, 'debug_user.html'), name='debug_user'),
    path('change-password/', change_password, name='change_password'),
    
    # ===== RÉINITIALISATION DE MOT DE PASSE ===== #
    path('password-reset/', password_reset, name='password_reset'),
    path('password-reset/code/', password_reset_code, name='password_reset_code'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    
    # ===== KYC ===== #
    path('kyc/status/', kyc_status, name='kyc_status'),
    path('kyc/upload/', kyc_upload, name='kyc_upload'),
    
    # ===== DASHBOARDS ===== #
    path('dashboard/user/', user_dashboard, name='user_dashboard'),
    path('dashboard/arbitre/', arbitre_dashboard, name='arbitre_dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    
    # ===== TRANSACTIONS ===== #
    path('transactions/create/', transaction_create, name='transaction_create'),
    path('transactions/buyer/', buyer_transactions, name='buyer_transactions'),
    path('transactions/seller/', seller_transactions, name='seller_transactions'),
    path('transactions/<int:transaction_id>/', transaction_detail, name='transaction_detail'),
    
    # ===== PAIEMENTS ===== #
    path('payments/methods/', payment_methods, name='payment_methods'),
    path('payments/history/', payment_history, name='payment_history'),
    
    # ===== LITIGES ===== #
    path('disputes/create/', dispute_create, name='dispute_create'),
    path('disputes/buyer/', buyer_disputes, name='buyer_disputes'),
    path('disputes/seller/', seller_disputes, name='seller_disputes'),
    path('disputes/arbitre/', arbitre_disputes, name='arbitre_disputes'),
    path('disputes/<int:dispute_id>/', dispute_detail, name='dispute_detail'),
    
    # ===== ADMIN ===== #
    path('admin/users/', admin_users, name='admin_users'),
    path('admin/kyc/pending/', admin_kyc_pending, name='admin_kyc_pending'),
    path('admin/kyc/approve/<int:user_id>/', admin_kyc_approve, name='admin_kyc_approve'),
    
    # ===== AJAX ENDPOINTS ===== #
    path('ajax/transaction/<int:transaction_id>/action/', ajax_transaction_action, name='ajax_transaction_action'),
    path('ajax/transaction/<int:transaction_id>/message/', ajax_send_message, name='ajax_send_message'),
    path('ajax/payment/<str:payment_reference>/status/', ajax_payment_status, name='ajax_payment_status'),
]