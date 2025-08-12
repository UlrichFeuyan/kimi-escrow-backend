#!/usr/bin/env python
"""
Script d'initialisation du projet Kimi Escrow
Ce script configure automatiquement le projet avec des données de base
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import GlobalSettings
from payments.models import PaymentMethod

User = get_user_model()


def create_default_settings():
    """Créer les paramètres par défaut"""
    settings_data = [
        ('ESCROW_COMMISSION_RATE', '0.025', 'Taux de commission escrow (2.5%)'),
        ('MINIMUM_ESCROW_AMOUNT', '1000', 'Montant minimum pour une transaction escrow (XAF)'),
        ('MAXIMUM_ESCROW_AMOUNT', '10000000', 'Montant maximum pour une transaction escrow (XAF)'),
        ('DISPUTE_TIMEOUT_DAYS', '7', 'Délai pour créer un litige (jours)'),
        ('AUTO_RELEASE_DAYS', '14', 'Délai de libération automatique des fonds (jours)'),
        ('KYC_REQUIRED', 'True', 'KYC obligatoire pour les transactions'),
        ('MAINTENANCE_MODE', 'False', 'Mode maintenance de l\'application'),
        ('SMS_ENABLED', 'True', 'Notifications SMS activées'),
        ('EMAIL_ENABLED', 'True', 'Notifications email activées'),
        ('MAX_UPLOAD_SIZE', '10485760', 'Taille maximum des fichiers uploadés (bytes)'),
    ]
    
    created_count = 0
    for key, value, description in settings_data:
        setting, created = GlobalSettings.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )
        if created:
            print(f"✓ Paramètre créé: {key} = {value}")
            created_count += 1
        else:
            print(f"- Paramètre existe déjà: {key} = {setting.value}")
    
    print(f"\n{created_count} nouveaux paramètres créés.")


def create_payment_methods():
    """Créer les méthodes de paiement par défaut"""
    payment_methods_data = [
        {
            'name': 'MTN Mobile Money',
            'provider': 'MTN_MOMO',
            'status': 'ACTIVE',
            'supports_collection': True,
            'supports_disbursement': True,
            'min_amount': 100,
            'max_amount': 1000000,
            'transaction_fee': 25,
            'description': 'Paiement via MTN Mobile Money Cameroun'
        },
        {
            'name': 'Orange Money',
            'provider': 'ORANGE_MONEY',
            'status': 'ACTIVE',
            'supports_collection': True,
            'supports_disbursement': True,
            'min_amount': 100,
            'max_amount': 1000000,
            'transaction_fee': 25,
            'description': 'Paiement via Orange Money Cameroun'
        },
        {
            'name': 'Virement Bancaire',
            'provider': 'BANK_TRANSFER',
            'status': 'ACTIVE',
            'supports_collection': True,
            'supports_disbursement': True,
            'min_amount': 1000,
            'max_amount': 50000000,
            'transaction_fee': 150,
            'description': 'Virement bancaire classique'
        },
        {
            'name': 'Compte Séquestre',
            'provider': 'ESCROW_BANK',
            'status': 'ACTIVE',
            'supports_collection': False,
            'supports_disbursement': True,
            'min_amount': 0,
            'max_amount': 999999999,
            'transaction_fee': 0,
            'description': 'Compte bancaire séquestre pour la sécurisation des fonds'
        },
    ]
    
    created_count = 0
    for method_data in payment_methods_data:
        method, created = PaymentMethod.objects.get_or_create(
            provider=method_data['provider'],
            defaults=method_data
        )
        if created:
            print(f"✓ Méthode de paiement créée: {method.name}")
            created_count += 1
        else:
            print(f"- Méthode existe déjà: {method.name}")
    
    print(f"\n{created_count} nouvelles méthodes de paiement créées.")


def create_test_users():
    """Créer des utilisateurs de test"""
    test_users_data = [
        {
            'phone_number': '+237612345678',
            'first_name': 'John',
            'last_name': 'Buyer',
            'role': 'BUYER',
            'kyc_status': 'VERIFIED',
            'is_phone_verified': True,
        },
        {
            'phone_number': '+237698765432',
            'first_name': 'Jane',
            'last_name': 'Seller',
            'role': 'SELLER',
            'kyc_status': 'VERIFIED',
            'is_phone_verified': True,
        },
        {
            'phone_number': '+237655555555',
            'first_name': 'Alex',
            'last_name': 'Arbitre',
            'role': 'ARBITRE',
            'kyc_status': 'VERIFIED',
            'is_phone_verified': True,
        },
        {
            'phone_number': '+237600000000',
            'first_name': 'Admin',
            'last_name': 'System',
            'role': 'ADMIN',
            'kyc_status': 'VERIFIED',
            'is_phone_verified': True,
            'is_staff': True,
            'is_superuser': True,
        },
    ]
    
    created_count = 0
    password = 'TestPassword123!'
    
    for user_data in test_users_data:
        phone = user_data['phone_number']
        if not User.objects.filter(phone_number=phone).exists():
            user = User.objects.create_user(
                password=password,
                **user_data
            )
            print(f"✓ Utilisateur créé: {user.get_full_name()} ({phone})")
            created_count += 1
        else:
            print(f"- Utilisateur existe déjà: {phone}")
    
    print(f"\n{created_count} nouveaux utilisateurs de test créés.")
    print(f"Mot de passe par défaut: {password}")


def run_migrations():
    """Exécuter les migrations"""
    print("🔄 Exécution des migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("✓ Migrations terminées.")


def collect_static():
    """Collecter les fichiers statiques"""
    print("🔄 Collecte des fichiers statiques...")
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
    print("✓ Fichiers statiques collectés.")


def main():
    """Fonction principale d'initialisation"""
    print("🚀 Initialisation du projet Kimi Escrow Backend")
    print("=" * 50)
    
    try:
        # 1. Migrations
        run_migrations()
        print()
        
        # 2. Paramètres par défaut
        print("📋 Création des paramètres par défaut...")
        create_default_settings()
        print()
        
        # 3. Méthodes de paiement
        print("💳 Création des méthodes de paiement...")
        create_payment_methods()
        print()
        
        # 4. Utilisateurs de test (seulement en développement)
        if os.getenv('DEBUG', 'True').lower() == 'true':
            print("👥 Création des utilisateurs de test...")
            create_test_users()
            print()
        
        # 5. Fichiers statiques
        collect_static()
        print()
        
        print("🎉 Initialisation terminée avec succès!")
        print()
        print("📝 Prochaines étapes:")
        print("1. Configurer vos variables d'environnement dans .env")
        print("2. Démarrer le serveur: python manage.py runserver")
        print("3. Démarrer Celery: celery -A kimi_escrow worker --loglevel=info")
        print("4. Accéder à l'admin: http://localhost:8000/admin/")
        print("5. Tester l'API: http://localhost:8000/api/core/health/")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
