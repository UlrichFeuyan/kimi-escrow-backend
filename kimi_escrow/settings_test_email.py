"""
Configuration de test avec Outlook/Hotmail pour contourner le problème Gmail
"""

from .settings import *

# Configuration Email Outlook/Hotmail - Alternative à Gmail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-mail.outlook.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'djofangulrich05@gmail.com'  # On garde le même pour l'instant
EMAIL_HOST_PASSWORD = 'khli jnrd otqh knki'  # App Password Gmail
DEFAULT_FROM_EMAIL = 'djofangulrich05@gmail.com'
SERVER_EMAIL = 'djofangulrich05@gmail.com'

# Configuration supplémentaire
SITE_URL = 'https://kimi-escrow.com'
SUPPORT_EMAIL = 'support@kimi-escrow.com'
EMAIL_TEMPLATE_DIR = 'emails/'
USE_CELERY = True

print("⚠️  ATTENTION: Configuration Outlook - EMAIL_HOST_USER doit être un compte Outlook!")
print("📧 Pour tester, créez un compte Outlook et mettez à jour EMAIL_HOST_USER et EMAIL_HOST_PASSWORD")
