from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router pour les ViewSets (si nécessaire)
router = DefaultRouter()

urlpatterns = [
    # Authentification
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),
    
    # Vérification téléphone
    path('verify-phone/', views.PhoneVerificationView.as_view(), name='verify-phone'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    
    # Profil utilisateur
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('change-password/', views.PasswordChangeView.as_view(), name='change-password'),
    
    # KYC
    path('kyc/upload/', views.KYCDocumentUploadView.as_view(), name='kyc-upload'),
    path('kyc/documents/', views.KYCDocumentListView.as_view(), name='kyc-documents'),
    path('kyc/status/', views.KYCStatusView.as_view(), name='kyc-status'),
    path('kyc/webhook/smile-id/', views.SmileIDWebhookView.as_view(), name='smile-id-webhook'),
    
    # Administration
    path('admin/users/', views.AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/kyc/<int:user_id>/approve/', views.AdminKYCApprovalView.as_view(), name='admin-kyc-approve'),
    path('admin/statistics/', views.user_statistics, name='admin-user-stats'),
    
    # Refresh token
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),
] + router.urls
