"""
Celery configuration for KIMI Escrow - Production
"""

import os
from celery import Celery
from decouple import config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings_production')

# Create the celery app
app = Celery('kimi_escrow')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configuration de production
app.conf.update(
    # Broker et backend
    broker_url=config('REDIS_URL'),
    result_backend=config('REDIS_URL'),
    
    # Sérialisation
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    
    # Timezone
    timezone='Africa/Douala',
    enable_utc=True,
    
    # Workers
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=200000,  # 200MB
    
    # Tasks
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    
    # Résultats
    result_expires=3600,  # 1 heure
    result_persistent=True,
    
    # Rate limiting
    task_annotations={
        'tasks.send_notification': {'rate_limit': '10/m'},
        'tasks.process_payment': {'rate_limit': '5/m'},
        'tasks.send_sms': {'rate_limit': '20/m'},
        'tasks.send_email': {'rate_limit': '50/m'},
    },
    
    # Retry policy
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Sécurité
    worker_disable_rate_limits=False,
    worker_hijack_root_logger=False,
    
    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    
    # Beat (scheduler)
    beat_schedule={
        'check-face-to-face-transactions': {
            'task': 'escrow.tasks.check_face_to_face_transactions',
            'schedule': 3600.0,  # Toutes les heures
        },
        'check-milestone-deadlines': {
            'task': 'escrow.tasks.check_milestone_deadlines',
            'schedule': 1800.0,  # Toutes les 30 minutes
        },
        'check-international-inspections': {
            'task': 'escrow.tasks.check_international_inspections',
            'schedule': 7200.0,  # Toutes les 2 heures
        },
        'send-payment-reminders': {
            'task': 'escrow.tasks.send_payment_reminders',
            'schedule': 86400.0,  # Tous les jours
        },
        'cleanup-expired-sessions': {
            'task': 'core.tasks.cleanup_expired_sessions',
            'schedule': 3600.0,  # Toutes les heures
        },
        'backup-database': {
            'task': 'core.tasks.backup_database',
            'schedule': 86400.0,  # Tous les jours
        },
        'update-exchange-rates': {
            'task': 'escrow.tasks.update_exchange_rates',
            'schedule': 3600.0,  # Toutes les heures
        },
        'sync-mobile-money-balances': {
            'task': 'payments.tasks.sync_mobile_money_balances',
            'schedule': 1800.0,  # Toutes les 30 minutes
        },
        'process-webhook-retries': {
            'task': 'core.tasks.process_webhook_retries',
            'schedule': 300.0,  # Toutes les 5 minutes
        },
        'cleanup-old-logs': {
            'task': 'core.tasks.cleanup_old_logs',
            'schedule': 604800.0,  # Toutes les semaines
        },
    },
    
    # Routes des tâches
    task_routes={
        'escrow.tasks.*': {'queue': 'escrow'},
        'payments.tasks.*': {'queue': 'payments'},
        'users.tasks.*': {'queue': 'users'},
        'disputes.tasks.*': {'queue': 'disputes'},
        'core.tasks.*': {'queue': 'default'},
    },
    
    # Configuration des queues
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'escrow': {
            'exchange': 'escrow',
            'routing_key': 'escrow',
        },
        'payments': {
            'exchange': 'payments',
            'routing_key': 'payments',
        },
        'users': {
            'exchange': 'users',
            'routing_key': 'users',
        },
        'disputes': {
            'exchange': 'disputes',
            'routing_key': 'disputes',
        },
        'high_priority': {
            'exchange': 'high_priority',
            'routing_key': 'high_priority',
        },
    },
    
    # Configuration des exchanges
    task_default_exchange='default',
    task_default_exchange_type='direct',
    
    # Configuration des workers
    worker_pool_restarts=True,
    worker_direct=True,
    
    # Configuration des résultats
    result_chord_join_timeout=3600,  # 1 heure
    result_chord_retry_interval=1,
    
    # Configuration des événements
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Configuration des timeouts
    broker_connection_timeout=30,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Configuration des pools
    worker_pool='prefork',
    worker_concurrency=4,  # Ajuster selon les ressources du serveur
    
    # Configuration des logs
    worker_log_color=True,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    
    # Configuration des erreurs
    task_remote_tracebacks=True,
    task_always_eager=False,
    
    # Configuration des sérialiseurs
    accept_content=['json', 'pickle'],
    task_serializer='json',
    result_serializer='json',
    event_serializer='json',
    
    # Configuration des compressions
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
    },
)

# Configuration des tâches spécifiques
app.conf.task_routes.update({
    'escrow.tasks.process_face_to_face_validation': {'queue': 'high_priority'},
    'escrow.tasks.process_milestone_payment': {'queue': 'high_priority'},
    'payments.tasks.process_mobile_money_payment': {'queue': 'high_priority'},
    'disputes.tasks.escalate_dispute': {'queue': 'high_priority'},
})

# Configuration des timeouts par tâche
app.conf.task_annotations.update({
    'escrow.tasks.process_face_to_face_validation': {
        'time_limit': 300,  # 5 minutes
        'soft_time_limit': 240,  # 4 minutes
    },
    'escrow.tasks.process_milestone_payment': {
        'time_limit': 600,  # 10 minutes
        'soft_time_limit': 540,  # 9 minutes
    },
    'payments.tasks.process_mobile_money_payment': {
        'time_limit': 180,  # 3 minutes
        'soft_time_limit': 150,  # 2.5 minutes
    },
    'escrow.tasks.update_exchange_rates': {
        'time_limit': 120,  # 2 minutes
        'soft_time_limit': 90,  # 1.5 minutes
    },
})

@app.task(bind=True)
def debug_task(self):
    """Tâche de debug pour tester Celery"""
    print(f'Request: {self.request!r}')

# Configuration des tâches de monitoring
@app.task(bind=True)
def health_check(self):
    """Vérification de santé du worker Celery"""
    return {
        'worker_id': self.request.id,
        'status': 'healthy',
        'timestamp': self.request.timestamp,
    }

# Configuration des tâches de maintenance
@app.task(bind=True)
def cleanup_worker_memory(self):
    """Nettoyage de la mémoire du worker"""
    import gc
    gc.collect()
    return {'memory_cleaned': True}

# Configuration des tâches d'erreur
@app.task(bind=True)
def handle_task_failure(self, task_id, exc, traceback):
    """Gestion des échecs de tâches"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject = f'Échec de tâche Celery: {self.request.task}'
    message = f"""
    Tâche: {self.request.task}
    ID: {task_id}
    Erreur: {exc}
    Traceback: {traceback}
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.SERVER_EMAIL],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Impossible d'envoyer l'email d'erreur: {e}")
    
    return {'error_handled': True}

# Configuration des tâches de monitoring des performances
@app.task(bind=True)
def monitor_task_performance(self):
    """Monitoring des performances des tâches"""
    from django.core.cache import cache
    from datetime import datetime
    
    # Collecte des statistiques
    stats = {
        'total_tasks': cache.get('celery_total_tasks', 0),
        'successful_tasks': cache.get('celery_successful_tasks', 0),
        'failed_tasks': cache.get('celery_failed_tasks', 0),
        'average_execution_time': cache.get('celery_avg_execution_time', 0),
        'timestamp': datetime.now().isoformat(),
    }
    
    # Mise à jour des statistiques
    cache.set('celery_performance_stats', stats, 3600)
    
    return stats

# Configuration des tâches de backup
@app.task(bind=True)
def backup_celery_data(self):
    """Sauvegarde des données Celery"""
    from django.core.cache import cache
    import json
    from datetime import datetime
    
    # Collecte des données
    backup_data = {
        'performance_stats': cache.get('celery_performance_stats', {}),
        'active_tasks': cache.get('celery_active_tasks', []),
        'failed_tasks': cache.get('celery_failed_tasks', []),
        'timestamp': datetime.now().isoformat(),
    }
    
    # Sauvegarde dans un fichier
    backup_file = f'/var/www/kimi-escrow/backups/celery_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    try:
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        return {'backup_created': backup_file}
    except Exception as e:
        return {'error': str(e)}

# Configuration des tâches de nettoyage
@app.task(bind=True)
def cleanup_celery_data(self):
    """Nettoyage des anciennes données Celery"""
    from django.core.cache import cache
    import os
    from datetime import datetime, timedelta
    
    # Nettoyage des anciens backups
    backup_dir = '/var/www/kimi-escrow/backups'
    retention_days = 7
    
    if os.path.exists(backup_dir):
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('celery_backup_'):
                file_path = os.path.join(backup_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                
                if file_time < cutoff_date:
                    try:
                        os.remove(file_path)
                        print(f"Supprimé: {filename}")
                    except Exception as e:
                        print(f"Erreur lors de la suppression de {filename}: {e}")
    
    # Nettoyage du cache
    cache.delete_pattern('celery_*')
    
    return {'cleanup_completed': True}
