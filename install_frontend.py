#!/usr/bin/env python3
"""
Script d'installation du frontend Kimi Escrow
Intègre automatiquement le frontend Django dans le projet existant
"""

import os
import sys
import shutil
from pathlib import Path

def print_step(step, message):
    """Affiche une étape de l'installation"""
    print(f"\n🔧 Étape {step}: {message}")
    print("=" * 50)

def update_settings_py():
    """Met à jour le fichier settings.py pour intégrer le frontend"""
    print_step(1, "Mise à jour de settings.py")
    
    settings_path = Path("kimi_escrow/settings.py")
    
    if not settings_path.exists():
        print("❌ Fichier settings.py non trouvé!")
        return False
    
    # Lire le contenu actuel
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si les modifications sont déjà présentes
    if 'STATICFILES_DIRS' in content and 'templates' in content:
        print("✅ Settings.py déjà configuré pour le frontend")
        return True
    
    # Ajouter la configuration des templates et fichiers statiques
    frontend_config = '''
# ===== CONFIGURATION FRONTEND ===== #

# Configuration des templates
TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']

# Configuration des fichiers statiques
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Messages framework pour les alertes
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Configuration API pour le frontend
API_BASE_URL = 'http://localhost:8000/api'

# Sessions pour le frontend
SESSION_COOKIE_AGE = 86400  # 24 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
'''
    
    # Ajouter à la fin du fichier
    with open(settings_path, 'a', encoding='utf-8') as f:
        f.write(frontend_config)
    
    print("✅ Settings.py mis à jour avec la configuration frontend")
    return True

def update_main_urls():
    """Met à jour le fichier URLs principal pour inclure les routes frontend"""
    print_step(2, "Mise à jour des URLs principales")
    
    main_urls_path = Path("kimi_escrow/urls.py")
    
    if not main_urls_path.exists():
        print("❌ Fichier urls.py principal non trouvé!")
        return False
    
    # Lire le contenu actuel
    with open(main_urls_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si les routes frontend sont déjà ajoutées
    if 'frontend_urls' in content:
        print("✅ URLs frontend déjà configurées")
        return True
    
    # Trouver les urlpatterns et ajouter les routes frontend
    if 'urlpatterns = [' in content:
        # Ajouter l'import
        if 'from django.urls import path, include' not in content:
            content = content.replace(
                'from django.urls import path',
                'from django.urls import path, include'
            )
        
        # Ajouter les routes frontend avant les routes API
        content = content.replace(
            'urlpatterns = [',
            '''urlpatterns = [
    # Frontend routes (avant API pour priorité)
    path('', include('frontend_urls')),
'''
        )
        
        with open(main_urls_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ URLs frontend ajoutées au fichier principal")
        return True
    else:
        print("❌ Structure urlpatterns non trouvée dans urls.py")
        return False

def create_frontend_app():
    """Crée un pseudo-app Django pour le frontend"""
    print_step(3, "Configuration de l'application frontend")
    
    # Créer le dossier frontend
    frontend_dir = Path("frontend")
    frontend_dir.mkdir(exist_ok=True)
    
    # Créer __init__.py
    (frontend_dir / "__init__.py").touch()
    
    # Créer apps.py
    apps_content = '''from django.apps import AppConfig

class FrontendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'frontend'
    verbose_name = 'Frontend Kimi Escrow'
'''
    
    with open(frontend_dir / "apps.py", 'w', encoding='utf-8') as f:
        f.write(apps_content)
    
    print("✅ Application frontend configurée")
    return True

def copy_frontend_files():
    """Copie les fichiers frontend dans leur structure finale"""
    print_step(4, "Organisation des fichiers frontend")
    
    files_to_copy = [
        ("frontend_forms.py", "frontend/forms.py"),
        ("frontend_views.py", "frontend/views.py"),
        ("frontend_urls.py", "frontend/urls.py"),
    ]
    
    for source, dest in files_to_copy:
        if Path(source).exists():
            # Créer le dossier de destination si nécessaire
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            print(f"✅ {source} → {dest}")
        else:
            print(f"⚠️  {source} non trouvé")
    
    # Vérifier que les dossiers templates et static existent
    for folder in ["templates", "static"]:
        if Path(folder).exists():
            print(f"✅ Dossier {folder} trouvé")
        else:
            print(f"❌ Dossier {folder} manquant!")
    
    return True

def update_installed_apps():
    """Ajoute l'app frontend aux INSTALLED_APPS"""
    print_step(5, "Ajout de l'app frontend")
    
    settings_path = Path("kimi_escrow/settings.py")
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "'frontend'," in content or '"frontend",' in content:
        print("✅ App frontend déjà dans INSTALLED_APPS")
        return True
    
    # Trouver INSTALLED_APPS et ajouter frontend
    if 'INSTALLED_APPS = [' in content:
        content = content.replace(
            'INSTALLED_APPS = [',
            '''INSTALLED_APPS = [
    'frontend',  # Frontend Django templates'''
        )
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ App frontend ajoutée aux INSTALLED_APPS")
        return True
    else:
        print("❌ INSTALLED_APPS non trouvé dans settings.py")
        return False

def create_superuser_script():
    """Crée un script pour créer un superutilisateur avec profil admin"""
    print_step(6, "Création du script superutilisateur")
    
    script_content = '''#!/usr/bin/env python3
"""
Script pour créer un superutilisateur admin pour le frontend
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

def create_admin_user():
    print("Création d'un utilisateur administrateur...")
    
    phone_number = input("Numéro de téléphone (+237XXXXXXXXX): ")
    if not phone_number.startswith('+237'):
        phone_number = '+237' + phone_number.replace('+', '').replace('237', '')
    
    first_name = input("Prénom: ")
    last_name = input("Nom: ")
    password = input("Mot de passe: ")
    
    try:
        # Créer l'utilisateur
        user = User.objects.create_user(
            phone_number=phone_number,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=True,
            is_phone_verified=True
        )
        
        # Créer le profil admin
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'ADMIN',
                'kyc_status': 'VERIFIED'
            }
        )
        
        print(f"✅ Utilisateur admin créé: {user.phone_number}")
        print(f"Nom: {user.get_full_name()}")
        print(f"Rôle: {profile.role}")
        print("🌐 Vous pouvez maintenant accéder au frontend!")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")

if __name__ == '__main__':
    create_admin_user()
'''
    
    with open("create_admin.py", 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Rendre exécutable
    os.chmod("create_admin.py", 0o755)
    
    print("✅ Script create_admin.py créé")
    return True

def create_frontend_management_command():
    """Crée une commande de management pour initialiser le frontend"""
    print_step(7, "Création de la commande de management frontend")
    
    # Créer la structure management/commands
    mgmt_dir = Path("frontend/management")
    mgmt_dir.mkdir(parents=True, exist_ok=True)
    
    # __init__.py files
    (mgmt_dir / "__init__.py").touch()
    
    commands_dir = mgmt_dir / "commands"
    commands_dir.mkdir(exist_ok=True)
    (commands_dir / "__init__.py").touch()
    
    # Commande init_frontend
    command_content = '''from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialise le frontend avec des données de démonstration'
    
    def handle(self, *args, **options):
        self.stdout.write('🚀 Initialisation du frontend Kimi Escrow...')
        
        # Créer des utilisateurs de test si pas en production
        if not User.objects.filter(phone_number='+237612345678').exists():
            # Acheteur de test
            buyer = User.objects.create_user(
                phone_number='+237612345678',
                password='test123',
                first_name='Jean',
                last_name='Acheteur',
                is_phone_verified=True
            )
            UserProfile.objects.create(
                user=buyer,
                role='BUYER',
                kyc_status='VERIFIED'
            )
            
            # Vendeur de test
            seller = User.objects.create_user(
                phone_number='+237698765432',
                password='test123',
                first_name='Marie',
                last_name='Vendeur',
                is_phone_verified=True
            )
            UserProfile.objects.create(
                user=seller,
                role='SELLER',
                kyc_status='VERIFIED'
            )
            
            self.stdout.write(
                self.style.SUCCESS('✅ Utilisateurs de test créés')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 Frontend initialisé avec succès!')
        )
'''
    
    with open(commands_dir / "init_frontend.py", 'w', encoding='utf-8') as f:
        f.write(command_content)
    
    print("✅ Commande de management init_frontend créée")
    return True

def show_next_steps():
    """Affiche les prochaines étapes après l'installation"""
    print_step(8, "Installation terminée!")
    
    next_steps = """
🎉 FRONTEND KIMI ESCROW INSTALLÉ AVEC SUCCÈS!

📋 Prochaines étapes:

1. 🔄 Appliquer les migrations:
   python manage.py migrate

2. 📦 Collecter les fichiers statiques:
   python manage.py collectstatic

3. 👤 Créer un utilisateur admin:
   python create_admin.py

4. 🧪 Initialiser avec des données de test:
   python manage.py init_frontend

5. 🚀 Lancer le serveur:
   python manage.py runserver

6. 🌐 Accéder au frontend:
   http://localhost:8000/

📚 Documentation:
   Consultez FRONTEND_README.md pour plus de détails

🎯 Fonctionnalités disponibles:
   ✅ Authentification complète avec RBAC
   ✅ Dashboards par rôle (BUYER, SELLER, ARBITRE, ADMIN)
   ✅ Gestion des transactions escrow
   ✅ Paiements Mobile Money
   ✅ Système de litiges
   ✅ Interface d'administration
   ✅ Design responsive Bootstrap 5
   ✅ Intégration AJAX avec API DRF

⚠️  Important:
   - Vérifiez que tous les endpoints DRF sont fonctionnels
   - Configurez les clés API Mobile Money
   - Testez les permissions et roles
   - Personnalisez les styles selon votre charte graphique

🆘 Support:
   En cas de problème, consultez le fichier FRONTEND_README.md
   ou contactez l'équipe de développement.
"""
    
    print(next_steps)

def main():
    """Fonction principale d'installation"""
    print("🎨 INSTALLATION DU FRONTEND KIMI ESCROW")
    print("======================================")
    
    # Vérifier qu'on est dans le bon répertoire
    if not Path("manage.py").exists():
        print("❌ Erreur: Veuillez exécuter ce script depuis la racine du projet Django")
        sys.exit(1)
    
    # Vérifier les dossiers nécessaires
    required_dirs = ["templates", "static"]
    missing_dirs = [d for d in required_dirs if not Path(d).exists()]
    
    if missing_dirs:
        print(f"❌ Erreur: Dossiers manquants: {', '.join(missing_dirs)}")
        print("Assurez-vous que tous les fichiers frontend ont été copiés.")
        sys.exit(1)
    
    # Exécuter les étapes d'installation
    steps = [
        update_settings_py,
        update_main_urls,
        create_frontend_app,
        copy_frontend_files,
        update_installed_apps,
        create_superuser_script,
        create_frontend_management_command,
        show_next_steps
    ]
    
    for step in steps:
        try:
            if not step():
                print(f"❌ Échec de l'étape: {step.__name__}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Erreur dans {step.__name__}: {e}")
            sys.exit(1)
    
    print("\n🎉 Installation terminée avec succès!")

if __name__ == "__main__":
    main()
