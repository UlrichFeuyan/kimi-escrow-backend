from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from django.core.cache import cache
from .models import AuditLog, GlobalSettings
from .serializers import AuditLogSerializer, GlobalSettingsSerializer
from .permissions import IsAdmin
from .utils import APIResponseMixin


class HealthCheckView(APIView):
    """
    Endpoint de vérification de l'état de santé de l'API
    """
    permission_classes = []
    
    def get(self, request):
        health_data = {
            'status': 'healthy',
            'database': 'connected',
            'cache': 'connected',
            'version': '1.0.0'
        }
        
        # Vérifier la connexion à la base de données
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            health_data['database'] = 'disconnected'
            health_data['status'] = 'unhealthy'
        
        # Vérifier la connexion au cache
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') != 'ok':
                raise Exception('Cache test failed')
        except Exception:
            health_data['cache'] = 'disconnected'
            health_data['status'] = 'unhealthy'
        
        status_code = 200 if health_data['status'] == 'healthy' else 503
        return Response(health_data, status=status_code)


class GlobalSettingsListView(generics.ListAPIView, APIResponseMixin):
    """
    Liste des paramètres globaux (lecture seule pour les utilisateurs authentifiés)
    """
    queryset = GlobalSettings.objects.all()
    serializer_class = GlobalSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Les utilisateurs normaux ne voient que certains paramètres
        if self.request.user.role != 'ADMIN':
            public_keys = [
                'ESCROW_COMMISSION_RATE',
                'MINIMUM_ESCROW_AMOUNT',
                'MAXIMUM_ESCROW_AMOUNT',
                'DISPUTE_TIMEOUT_DAYS',
                'AUTO_RELEASE_DAYS'
            ]
            return GlobalSettings.objects.filter(key__in=public_keys)
        return GlobalSettings.objects.all()


class AuditLogListView(generics.ListAPIView, APIResponseMixin):
    """
    Liste des logs d'audit (admin et arbitres seulement)
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['action', 'resource_type', 'user']
    search_fields = ['user__phone_number', 'resource_id', 'details']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrer par utilisateur si spécifié
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filtrer par période
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
