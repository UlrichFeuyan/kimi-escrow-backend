#!/usr/bin/env python3
"""
Script d'optimisation pour la production - Kimi Escrow Frontend
Optimise les performances et prépare le déploiement
"""

import os
import sys
import django
from pathlib import Path
import subprocess
import shutil
from colorama import Fore, Style, init

# Initialiser colorama
init(autoreset=True)

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')
django.setup()

from django.core.management import call_command
from django.conf import settings

class ProductionOptimizer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.static_root = Path(settings.STATIC_ROOT) if settings.STATIC_ROOT else self.project_root / 'staticfiles'
        self.optimizations_applied = []
        
    def print_header(self, title):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title.center(60)}")
        print(f"{Fore.CYAN}{'='*60}")

    def print_success(self, message):
        print(f"{Fore.GREEN}✓ {message}")
        self.optimizations_applied.append(message)

    def print_info(self, message):
        print(f"{Fore.BLUE}ℹ {message}")

    def print_warning(self, message):
        print(f"{Fore.YELLOW}⚠ {message}")

    def collect_static_files(self):
        """Collecter les fichiers statiques"""
        self.print_header("Collection des Fichiers Statiques")
        
        try:
            # Supprimer les anciens fichiers statiques
            if self.static_root.exists():
                shutil.rmtree(self.static_root)
                self.print_info("Anciens fichiers statiques supprimés")
            
            # Collecter les nouveaux fichiers
            call_command('collectstatic', '--noinput', verbosity=0)
            self.print_success("Fichiers statiques collectés")
            
        except Exception as e:
            print(f"{Fore.RED}✗ Erreur lors de la collection: {str(e)}")

    def optimize_css(self):
        """Optimiser les fichiers CSS"""
        self.print_header("Optimisation CSS")
        
        css_files = list(self.static_root.glob('**/*.css'))
        
        for css_file in css_files:
            if css_file.name.endswith('.min.css'):
                continue  # Déjà minifié
                
            try:
                # Lire le contenu
                content = css_file.read_text(encoding='utf-8')
                original_size = len(content)
                
                # Optimisations basiques
                # Supprimer les commentaires
                import re
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                
                # Supprimer les espaces inutiles
                content = re.sub(r'\s+', ' ', content)
                content = re.sub(r';\s*}', '}', content)
                content = re.sub(r'{\s*', '{', content)
                content = re.sub(r'}\s*', '}', content)
                content = re.sub(r':\s*', ':', content)
                content = re.sub(r';\s*', ';', content)
                
                # Écrire le fichier optimisé
                css_file.write_text(content.strip(), encoding='utf-8')
                
                new_size = len(content)
                reduction = ((original_size - new_size) / original_size) * 100
                
                self.print_success(f"CSS optimisé: {css_file.name} (-{reduction:.1f}%)")
                
            except Exception as e:
                self.print_warning(f"Erreur optimisation {css_file.name}: {str(e)}")

    def optimize_js(self):
        """Optimiser les fichiers JavaScript"""
        self.print_header("Optimisation JavaScript")
        
        js_files = list(self.static_root.glob('**/*.js'))
        
        for js_file in js_files:
            if js_file.name.endswith('.min.js'):
                continue  # Déjà minifié
                
            try:
                # Lire le contenu
                content = js_file.read_text(encoding='utf-8')
                original_size = len(content)
                
                # Optimisations basiques
                import re
                # Supprimer les commentaires de ligne
                content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
                
                # Supprimer les commentaires de bloc
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                
                # Supprimer les espaces inutiles (conservateur)
                content = re.sub(r'\n\s*\n', '\n', content)
                content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)
                
                # Écrire le fichier optimisé
                js_file.write_text(content.strip(), encoding='utf-8')
                
                new_size = len(content)
                reduction = ((original_size - new_size) / original_size) * 100
                
                self.print_success(f"JS optimisé: {js_file.name} (-{reduction:.1f}%)")
                
            except Exception as e:
                self.print_warning(f"Erreur optimisation {js_file.name}: {str(e)}")

    def create_gzip_files(self):
        """Créer des versions gzip des fichiers statiques"""
        self.print_header("Création des Fichiers Gzip")
        
        import gzip
        
        # Extensions à compresser
        extensions = ['.css', '.js', '.html', '.json', '.svg']
        
        for ext in extensions:
            files = list(self.static_root.glob(f'**/*{ext}'))
            
            for file_path in files:
                if file_path.suffix in extensions:
                    try:
                        # Lire le fichier original
                        content = file_path.read_bytes()
                        
                        # Créer la version gzip
                        gz_path = file_path.with_suffix(file_path.suffix + '.gz')
                        with gzip.open(gz_path, 'wb') as gz_file:
                            gz_file.write(content)
                        
                        # Calculer la compression
                        original_size = len(content)
                        compressed_size = gz_path.stat().st_size
                        reduction = ((original_size - compressed_size) / original_size) * 100
                        
                        if reduction > 10:  # Seulement si compression significative
                            self.print_success(f"Gzip créé: {file_path.name} (-{reduction:.1f}%)")
                        else:
                            gz_path.unlink()  # Supprimer si pas efficace
                            
                    except Exception as e:
                        self.print_warning(f"Erreur gzip {file_path.name}: {str(e)}")

    def optimize_images(self):
        """Optimiser les images"""
        self.print_header("Optimisation des Images")
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg']
        
        for ext in image_extensions:
            images = list(self.static_root.glob(f'**/*{ext}'))
            
            for image_path in images:
                try:
                    original_size = image_path.stat().st_size
                    
                    if ext.lower() in ['.jpg', '.jpeg', '.png']:
                        # Tentative d'optimisation avec Pillow si disponible
                        try:
                            from PIL import Image
                            
                            img = Image.open(image_path)
                            
                            # Optimiser la qualité
                            if ext.lower() in ['.jpg', '.jpeg']:
                                img.save(image_path, 'JPEG', quality=85, optimize=True)
                            elif ext.lower() == '.png':
                                img.save(image_path, 'PNG', optimize=True)
                            
                            new_size = image_path.stat().st_size
                            if new_size < original_size:
                                reduction = ((original_size - new_size) / original_size) * 100
                                self.print_success(f"Image optimisée: {image_path.name} (-{reduction:.1f}%)")
                                
                        except ImportError:
                            self.print_warning("Pillow non installé - optimisation images sautée")
                            break
                            
                except Exception as e:
                    self.print_warning(f"Erreur optimisation {image_path.name}: {str(e)}")

    def create_manifest(self):
        """Créer un manifeste des fichiers statiques"""
        self.print_header("Création du Manifeste")
        
        import json
        import hashlib
        from datetime import datetime
        
        manifest = {
            'generated': datetime.now().isoformat(),
            'files': {},
            'optimizations': self.optimizations_applied
        }
        
        # Calculer les hash des fichiers
        for file_path in self.static_root.rglob('*'):
            if file_path.is_file() and not file_path.name.endswith('.gz'):
                relative_path = file_path.relative_to(self.static_root)
                
                # Calculer le hash MD5
                hasher = hashlib.md5()
                hasher.update(file_path.read_bytes())
                file_hash = hasher.hexdigest()[:8]
                
                manifest['files'][str(relative_path)] = {
                    'hash': file_hash,
                    'size': file_path.stat().st_size,
                    'gzipped': file_path.with_suffix(file_path.suffix + '.gz').exists()
                }
        
        # Sauvegarder le manifeste
        manifest_path = self.static_root / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        
        self.print_success(f"Manifeste créé: {len(manifest['files'])} fichiers")

    def check_production_settings(self):
        """Vérifier les paramètres de production"""
        self.print_header("Vérification des Paramètres")
        
        # DEBUG doit être False
        if settings.DEBUG:
            self.print_warning("DEBUG est True - à désactiver en production")
        else:
            self.print_success("DEBUG désactivé")
        
        # ALLOWED_HOSTS doit être configuré
        if settings.ALLOWED_HOSTS == ['*'] or not settings.ALLOWED_HOSTS:
            self.print_warning("ALLOWED_HOSTS à configurer pour la production")
        else:
            self.print_success("ALLOWED_HOSTS configuré")
        
        # SECRET_KEY ne doit pas être hardcodée
        if hasattr(settings, 'SECRET_KEY') and len(settings.SECRET_KEY) > 20:
            self.print_success("SECRET_KEY configurée")
        else:
            self.print_warning("SECRET_KEY à vérifier")
        
        # CSRF settings
        if hasattr(settings, 'CSRF_COOKIE_SECURE'):
            self.print_success("Paramètres CSRF configurés")
        else:
            self.print_warning("Paramètres CSRF à configurer pour HTTPS")

    def create_deployment_script(self):
        """Créer un script de déploiement"""
        self.print_header("Création du Script de Déploiement")
        
        deploy_script = """#!/bin/bash
# Script de déploiement Kimi Escrow Frontend

set -e

echo "🚀 Déploiement Kimi Escrow Frontend"
echo "=================================="

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

# Migrations de base de données
echo "🗄️  Migrations base de données..."
python manage.py migrate

# Collecter les fichiers statiques
echo "📁 Collection des fichiers statiques..."
python manage.py collectstatic --noinput

# Optimiser pour la production
echo "⚡ Optimisation pour la production..."
python optimize_production.py

# Redémarrer les services (à adapter selon votre infrastructure)
echo "🔄 Redémarrage des services..."
# sudo systemctl restart gunicorn
# sudo systemctl restart nginx

echo "✅ Déploiement terminé avec succès!"
echo "🌐 Le frontend est prêt pour la production"
"""
        
        deploy_path = self.project_root / 'deploy.sh'
        deploy_path.write_text(deploy_script)
        deploy_path.chmod(0o755)
        
        self.print_success("Script de déploiement créé: deploy.sh")

    def run_optimization(self):
        """Exécuter toutes les optimisations"""
        print(f"{Fore.MAGENTA}{Style.BRIGHT}")
        print("🚀 KIMI ESCROW - Optimisation Production")
        print("=======================================")
        
        try:
            self.collect_static_files()
            self.optimize_css()
            self.optimize_js()
            self.create_gzip_files()
            self.optimize_images()
            self.create_manifest()
            self.check_production_settings()
            self.create_deployment_script()
            
            # Résumé
            self.print_header("Résumé des Optimisations")
            print(f"{Fore.GREEN}✅ Optimisations appliquées: {len(self.optimizations_applied)}")
            
            for optimization in self.optimizations_applied[:10]:  # Afficher les 10 premières
                print(f"{Fore.GREEN}  • {optimization}")
            
            if len(self.optimizations_applied) > 10:
                print(f"{Fore.GREEN}  • ... et {len(self.optimizations_applied) - 10} autres")
            
            print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 Frontend optimisé pour la production!")
            print(f"{Fore.CYAN}📝 Fichiers statiques dans: {self.static_root}")
            print(f"{Fore.CYAN}🚀 Utilisez deploy.sh pour déployer")
            
            return True
            
        except Exception as e:
            print(f"\n{Fore.RED}💥 Erreur durant l'optimisation: {str(e)}")
            return False


def main():
    """Point d'entrée principal"""
    optimizer = ProductionOptimizer()
    
    try:
        success = optimizer.run_optimization()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Optimisation interrompue")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}💥 Erreur inattendue: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
