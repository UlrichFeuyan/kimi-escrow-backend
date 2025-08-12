from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

urlpatterns = [
    # Transactions
    path('transactions/', views.EscrowTransactionListCreateView.as_view(), name='transaction-list-create'),
    path('transactions/<int:pk>/', views.EscrowTransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/<int:pk>/actions/', views.TransactionActionView.as_view(), name='transaction-actions'),
    
    # Messages de transaction
    path('transactions/<int:transaction_id>/messages/', 
         views.TransactionMessageListCreateView.as_view(), name='transaction-messages'),
    
    # Statistiques
    path('statistics/', views.transaction_statistics, name='transaction-statistics'),
    
] + router.urls
