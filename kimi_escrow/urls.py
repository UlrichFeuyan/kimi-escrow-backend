"""
URL configuration for kimi_escrow project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Configuration du schema Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Kimi Escrow API",
        default_version='v1',
        description="""
        API complète pour la plateforme d'escrow Kimi.
        
        ## Fonctionnalités principales:
        - 🔐 Authentification JWT avec rôles (BUYER, SELLER, ARBITRE, ADMIN)
        - 👤 Gestion des utilisateurs et vérification KYC (Smile ID)
        - 💰 Transactions escrow avec jalons et preuves
        - 💳 Intégration Mobile Money (MTN & Orange Money)
        - ⚖️ Système de litiges et d'arbitrage
        - 📱 Notifications SMS et emails
        - 🔒 Audit trail complet
        
        ## Authentification:
        Utilisez le token JWT dans l'en-tête Authorization: `Bearer <votre_token>`
        
        ## Utilisateurs de test:
        - **Admin**: +237600000000 / TestPassword123!
        - **Acheteur**: +237612345678 / TestPassword123!
        - **Vendeur**: +237698765432 / TestPassword123!
        - **Arbitre**: +237655555555 / TestPassword123!
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@kimi-escrow.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API Endpoints
    path('api/auth/', include('users.urls')),
    path('api/escrow/', include('escrow.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/disputes/', include('disputes.urls')),
    path('api/core/', include('core.urls')),
    
    # Frontend Django Templates (doit être en dernier pour catch-all)
    path('', include('frontend_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
