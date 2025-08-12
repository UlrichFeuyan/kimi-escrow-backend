from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.GlobalSettingsListView.as_view(), name='global-settings'),
    path('audit-logs/', views.AuditLogListView.as_view(), name='audit-logs'),
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
]