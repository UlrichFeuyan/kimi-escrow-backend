from django.urls import path
from . import views

urlpatterns = [
    # Mobile Money
    path('momo/collect/', views.MobileMoneyCollectionView.as_view(), name='momo-collect'),
    path('momo/status/<str:reference>/', views.PaymentStatusView.as_view(), name='payment-status'),
    
    # Webhooks
    path('webhooks/mtn/', views.MTNWebhookView.as_view(), name='mtn-webhook'),
    path('webhooks/orange/', views.OrangeWebhookView.as_view(), name='orange-webhook'),
    
    # Gestion des paiements
    path('methods/', views.PaymentMethodListView.as_view(), name='payment-methods'),
    path('history/', views.PaymentHistoryView.as_view(), name='payment-history'),
]
