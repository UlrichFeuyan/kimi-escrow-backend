"""
Configuration Gunicorn pour KIMI Escrow - Production
"""

import multiprocessing
import os
from pathlib import Path

# Configuration des workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Configuration du binding
bind = '127.0.0.1:8000'
backlog = 2048

# Configuration des timeouts
timeout = 120
keepalive = 2
graceful_timeout = 30

# Configuration des logs
accesslog = '/var/www/kimi-escrow/logs/gunicorn_access.log'
errorlog = '/var/www/kimi-escrow/logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Configuration de sécurité
user = 'kimi_escrow'
group = 'kimi_escrow'
tmp_upload_dir = None

# Configuration des processus
preload_app = True
daemon = False
pidfile = '/var/www/kimi-escrow/logs/gunicorn.pid'
worker_tmp_dir = '/dev/shm'

# Configuration des limites
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Configuration des headers
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Configuration des hooks
def on_starting(server):
    """Hook appelé au démarrage du serveur"""
    server.log.info("Démarrage de KIMI Escrow Gunicorn")

def on_reload(server):
    """Hook appelé lors du rechargement"""
    server.log.info("Rechargement de KIMI Escrow Gunicorn")

def on_exit(server):
    """Hook appelé à l'arrêt du serveur"""
    server.log.info("Arrêt de KIMI Escrow Gunicorn")

def worker_int(worker):
    """Hook appelé lors de l'interruption d'un worker"""
    worker.log.info("Worker %s interrompu", worker.pid)

def pre_fork(server, worker):
    """Hook appelé avant la création d'un worker"""
    server.log.info("Création du worker %s", worker.pid)

def post_fork(server, worker):
    """Hook appelé après la création d'un worker"""
    server.log.info("Worker %s créé", worker.pid)

def post_worker_init(worker):
    """Hook appelé après l'initialisation d'un worker"""
    worker.log.info("Worker %s initialisé", worker.pid)

def worker_abort(worker):
    """Hook appelé lors de l'abort d'un worker"""
    worker.log.info("Worker %s aborted", worker.pid)

def pre_exec(server):
    """Hook appelé avant l'exécution"""
    server.log.info("Exécution de KIMI Escrow Gunicorn")

def when_ready(server):
    """Hook appelé quand le serveur est prêt"""
    server.log.info("KIMI Escrow Gunicorn prêt sur %s", server.address)

def on_exit(server):
    """Hook appelé à la sortie"""
    server.log.info("Sortie de KIMI Escrow Gunicorn")

# Configuration des callbacks
def post_request(worker, req, environ, resp):
    """Callback appelé après chaque requête"""
    # Log des métriques de performance
    if hasattr(worker, 'request_count'):
        worker.request_count += 1
    else:
        worker.request_count = 1
    
    # Log des requêtes lentes (> 1 seconde)
    if hasattr(req, 'start_time'):
        duration = time.time() - req.start_time
        if duration > 1.0:
            worker.log.warning("Requête lente: %s - %.2fs", req.uri, duration)

def pre_request(worker, req):
    """Callback appelé avant chaque requête"""
    req.start_time = time.time()

# Configuration des middlewares
def process_request(worker, req, environ):
    """Middleware de traitement des requêtes"""
    # Ajout d'en-têtes de sécurité
    environ['HTTP_X_FORWARDED_FOR'] = environ.get('HTTP_X_FORWARDED_FOR', '')
    environ['HTTP_X_REAL_IP'] = environ.get('HTTP_X_REAL_IP', '')
    
    # Log des informations de la requête
    worker.log.info("Requête: %s %s - IP: %s", 
                   environ.get('REQUEST_METHOD', ''),
                   environ.get('REQUEST_URI', ''),
                   environ.get('REMOTE_ADDR', ''))

# Configuration des signaux
def worker_exit(server, worker):
    """Callback appelé lors de la sortie d'un worker"""
    server.log.info("Worker %s sorti", worker.pid)

# Configuration des métriques
def worker_stats(worker):
    """Callback pour les statistiques des workers"""
    stats = {
        'worker_id': worker.pid,
        'requests_processed': getattr(worker, 'request_count', 0),
        'memory_usage': worker.memory_usage if hasattr(worker, 'memory_usage') else 0,
        'cpu_usage': worker.cpu_usage if hasattr(worker, 'cpu_usage') else 0,
    }
    
    # Sauvegarde des statistiques dans un fichier ou cache
    stats_file = f'/var/www/kimi-escrow/logs/worker_{worker.pid}_stats.json'
    try:
        import json
        with open(stats_file, 'w') as f:
            json.dump(stats, f)
    except Exception as e:
        worker.log.error("Erreur lors de la sauvegarde des statistiques: %s", e)

# Configuration des timeouts par type de requête
def worker_timeout(worker, req):
    """Configuration des timeouts par type de requête"""
    # Timeouts plus longs pour les opérations lourdes
    if req.uri.startswith('/api/escrow/transactions/'):
        return 300  # 5 minutes pour les transactions escrow
    elif req.uri.startswith('/api/payments/'):
        return 180  # 3 minutes pour les paiements
    elif req.uri.startswith('/admin/'):
        return 60   # 1 minute pour l'admin
    else:
        return 30   # 30 secondes par défaut

# Configuration des limites de mémoire
def worker_memory_limit(worker):
    """Configuration des limites de mémoire par worker"""
    import psutil
    import os
    
    process = psutil.Process(worker.pid)
    memory_info = process.memory_info()
    
    # Limite de mémoire à 512MB par worker
    memory_limit = 512 * 1024 * 1024  # 512MB en bytes
    
    if memory_info.rss > memory_limit:
        worker.log.warning("Worker %s dépasse la limite de mémoire: %.2f MB", 
                          worker.pid, memory_info.rss / 1024 / 1024)
        
        # Redémarrage du worker si nécessaire
        if memory_info.rss > memory_limit * 1.5:  # 768MB
            worker.log.error("Worker %s redémarré pour cause de mémoire", worker.pid)
            worker.alive = False

# Configuration des health checks
def health_check(worker):
    """Health check des workers"""
    import psutil
    import os
    
    process = psutil.Process(worker.pid)
    
    # Vérification de la santé du processus
    if not process.is_running():
        worker.log.error("Worker %s n'est plus en cours d'exécution", worker.pid)
        return False
    
    # Vérification de la mémoire
    memory_info = process.memory_info()
    if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
        worker.log.warning("Worker %s utilise trop de mémoire: %.2f MB", 
                          worker.pid, memory_info.rss / 1024 / 1024)
    
    # Vérification du CPU
    cpu_percent = process.cpu_percent()
    if cpu_percent > 80:
        worker.log.warning("Worker %s utilise trop de CPU: %.1f%%", 
                          worker.pid, cpu_percent)
    
    return True

# Configuration des logs structurés
def structured_logging(worker, req, environ, resp):
    """Logging structuré des requêtes"""
    import json
    import time
    
    log_data = {
        'timestamp': time.time(),
        'worker_id': worker.pid,
        'method': environ.get('REQUEST_METHOD', ''),
        'uri': environ.get('REQUEST_URI', ''),
        'status': resp.status_code if hasattr(resp, 'status_code') else 0,
        'user_agent': environ.get('HTTP_USER_AGENT', ''),
        'ip_address': environ.get('REMOTE_ADDR', ''),
        'forwarded_for': environ.get('HTTP_X_FORWARDED_FOR', ''),
        'real_ip': environ.get('HTTP_X_REAL_IP', ''),
        'response_time': getattr(req, 'response_time', 0),
        'request_size': environ.get('CONTENT_LENGTH', 0),
        'response_size': len(resp.body) if hasattr(resp, 'body') else 0,
    }
    
    # Sauvegarde dans un fichier de log structuré
    log_file = '/var/www/kimi-escrow/logs/structured_access.log'
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_data) + '\n')
    except Exception as e:
        worker.log.error("Erreur lors de l'écriture du log structuré: %s", e)

# Configuration des métriques de performance
def performance_metrics(worker, req, environ, resp):
    """Collecte des métriques de performance"""
    import time
    import json
    
    if hasattr(req, 'start_time'):
        response_time = time.time() - req.start_time
        
        metrics = {
            'timestamp': time.time(),
            'worker_id': worker.pid,
            'uri': environ.get('REQUEST_URI', ''),
            'method': environ.get('REQUEST_METHOD', ''),
            'response_time': response_time,
            'status_code': resp.status_code if hasattr(resp, 'status_code') else 0,
        }
        
        # Sauvegarde des métriques
        metrics_file = '/var/www/kimi-escrow/logs/performance_metrics.json'
        try:
            # Lecture des métriques existantes
            existing_metrics = []
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r') as f:
                    existing_metrics = json.load(f)
            
            # Ajout des nouvelles métriques
            existing_metrics.append(metrics)
            
            # Limitation à 1000 métriques
            if len(existing_metrics) > 1000:
                existing_metrics = existing_metrics[-1000:]
            
            # Sauvegarde
            with open(metrics_file, 'w') as f:
                json.dump(existing_metrics, f, indent=2)
                
        except Exception as e:
            worker.log.error("Erreur lors de la sauvegarde des métriques: %s", e)

# Configuration des callbacks de fin de requête
def post_request_callback(worker, req, environ, resp):
    """Callback appelé après chaque requête"""
    # Calcul du temps de réponse
    if hasattr(req, 'start_time'):
        req.response_time = time.time() - req.start_time
    
    # Appel des différents callbacks
    post_request(worker, req, environ, resp)
    structured_logging(worker, req, environ, resp)
    performance_metrics(worker, req, environ, resp)
    
    # Vérification de la santé du worker
    if not health_check(worker):
        worker.log.error("Worker %s en mauvaise santé", worker.pid)
    
    # Vérification de la mémoire
    worker_memory_limit(worker)
    
    # Statistiques du worker
    worker_stats(worker)

# Configuration des callbacks de début de requête
def pre_request_callback(worker, req):
    """Callback appelé avant chaque requête"""
    pre_request(worker, req)
    process_request(worker, req, req.environ)
    
    # Configuration du timeout
    timeout_value = worker_timeout(worker, req)
    if hasattr(req, 'set_timeout'):
        req.set_timeout(timeout_value)

# Configuration des hooks de Gunicorn
def when_ready(server):
    """Hook appelé quand le serveur est prêt"""
    server.log.info("KIMI Escrow Gunicorn prêt sur %s", server.address)
    
    # Création des dossiers de logs s'ils n'existent pas
    log_dirs = [
        '/var/www/kimi-escrow/logs',
        '/var/www/kimi-escrow/backups',
        '/var/www/kimi-escrow/media'
    ]
    
    for log_dir in log_dirs:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configuration des permissions
    for log_dir in log_dirs:
        try:
            os.chown(log_dir, 1000, 1000)  # kimi_escrow user/group
        except Exception as e:
            server.log.warning("Impossible de changer les permissions de %s: %s", log_dir, e)

def on_starting(server):
    """Hook appelé au démarrage du serveur"""
    server.log.info("Démarrage de KIMI Escrow Gunicorn")
    
    # Import des modules Django
    import django
    from django.conf import settings
    
    # Configuration Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings_production')
    django.setup()
    
    server.log.info("Django configuré avec succès")

def on_exit(server):
    """Hook appelé à la sortie"""
    server.log.info("Arrêt de KIMI Escrow Gunicorn")
    
    # Nettoyage des fichiers temporaires
    import tempfile
    import shutil
    
    temp_dir = '/dev/shm/gunicorn_*'
    try:
        import glob
        for temp_path in glob.glob(temp_dir):
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
    except Exception as e:
        server.log.warning("Erreur lors du nettoyage des fichiers temporaires: %s", e)

# Configuration des callbacks
post_request = post_request_callback
pre_request = pre_request_callback
