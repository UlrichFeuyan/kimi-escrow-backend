"""
Configuration spécifique pour Gmail - Mode Production
Utilisez ce fichier en production avec vos vrais identifiants
"""

from .settings import *

# Configuration Email Gmail - Production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'djofangulrich05@gmail.com'
EMAIL_HOST_PASSWORD = 'khli jnrd otqh knki'  # App Password Gmail
DEFAULT_FROM_EMAIL = 'Kimi Escrow <djofangulrich05@gmail.com>'
SERVER_EMAIL = 'djofangulrich05@gmail.com'

# Configuration supplémentaire pour les emails
SITE_URL = 'https://kimi-escrow.com'
SUPPORT_EMAIL = 'support@kimi-escrow.com'

# Désactiver le mode console en production
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Déjà défini ci-dessus

# Templates d'email
EMAIL_TEMPLATE_DIR = 'emails/'

# Activer Celery en production
USE_CELERY = True

# Note: Assurez-vous que EMAIL_HOST_PASSWORD est un App Password valide
# et non votre mot de passe normal de compte Google
