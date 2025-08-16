#!/usr/bin/env python3
"""
Test de la configuration email
"""

import os
import django
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMessage

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')
django.setup()

def test_email_configuration():
    """Tester la configuration email"""
    print("🔧 Test de la configuration email")
    print("=" * 50)
    
    # Afficher la configuration actuelle
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"DEBUG: {settings.DEBUG}")
    
    print("\n📧 Test d'envoi d'email...")
    
    try:
        # Test avec send_mail
        result = send_mail(
            subject='Test Email - Kimi Escrow',
            message='Ceci est un email de test pour vérifier la configuration SMTP.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['test@example.com'],
            fail_silently=False,
        )
        
        if result:
            print("✅ Email envoyé avec succès via send_mail!")
        else:
            print("❌ Échec de l'envoi via send_mail")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi via send_mail: {e}")
    
    try:
        # Test avec EmailMessage
        email = EmailMessage(
            subject='Test EmailMessage - Kimi Escrow',
            body='Ceci est un test avec EmailMessage.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['test@example.com'],
        )
        
        result = email.send(fail_silently=False)
        
        if result:
            print("✅ Email envoyé avec succès via EmailMessage!")
        else:
            print("❌ Échec de l'envoi via EmailMessage")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi via EmailMessage: {e}")
    
    print("\n📋 Recommandations:")
    
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        print("- ✅ Backend console actif (parfait pour les tests)")
        print("- Les emails s'affichent dans la console Django")
    elif settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        print("- 🔧 Backend SMTP actif")
        if not settings.EMAIL_HOST_PASSWORD:
            print("- ⚠️  EMAIL_HOST_PASSWORD non configuré")
        else:
            print("- ✅ EMAIL_HOST_PASSWORD configuré")
    
    print("\n🔍 Pour résoudre les problèmes Gmail:")
    print("1. Vérifiez que vous utilisez un 'App Password' de 16 caractères")
    print("2. Pas votre mot de passe normal de compte Google")
    print("3. Activez l'authentification à 2 facteurs sur votre compte Google")
    print("4. Générez un App Password spécifique pour 'Mail'")

if __name__ == "__main__":
    test_email_configuration()
