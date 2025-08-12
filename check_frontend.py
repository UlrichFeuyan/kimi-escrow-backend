#!/usr/bin/env python3
"""
Script de vérification du frontend Kimi Escrow
Vérifie l'intégrité des templates, URLs et fonctionnalités
"""

import os
import sys
import django
from pathlib import Path
import requests
from urllib.parse import urljoin
import time
from colorama import Fore, Style, init

# Initialiser colorama pour les couleurs
init(autoreset=True)

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')
django.setup()

from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

class FrontendChecker:
    def __init__(self):
        self.client = Client()
        self.base_url = 'http://127.0.0.1:8000'
        self.errors = []
        self.warnings = []
        self.success_count = 0
        
        # URLs à tester
        self.urls_to_test = [
            ('home', {}),
            ('login', {}),
            ('register', {}),
            ('buyer_dashboard', {}),
            ('seller_dashboard', {}),
            ('admin_dashboard', {}),
            ('arbitre_dashboard', {}),
            ('transaction_create', {}),
            ('buyer_transactions', {}),
            ('seller_transactions', {}),
            ('kyc_status', {}),
            ('kyc_upload', {}),
            ('buyer_disputes', {}),
            ('payment_methods', {}),
            ('profile', {}),
            ('change_password', {}),
            ('verify_phone', {}),
        ]
        
        # URLs avec paramètres
        self.parameterized_urls = [
            ('transaction_detail', {'transaction_id': 1}),
            ('dispute_detail', {'dispute_id': 1}),
            ('admin_kyc_approve', {'user_id': 1}),
        ]
        
        # Templates requis
        self.required_templates = [
            'base.html',
            'home.html',
            'users/login.html',
            'users/register.html',
            'users/profile.html',
            'users/verify_phone.html',
            'users/change_password.html',
            'users/kyc_status.html',
            'dashboards/buyer_dashboard.html',
            'dashboards/seller_dashboard.html',
            'dashboards/admin_dashboard.html',
            'dashboards/arbitre_dashboard.html',
            'escrow/transaction_create.html',
            'escrow/transaction_detail.html',
            'escrow/buyer_transactions.html',
            'escrow/seller_transactions.html',
            'disputes/buyer_disputes.html',
            'disputes/dispute_detail.html',
            'payments/payment_methods.html',
        ]
        
        # Fichiers statiques requis
        self.required_static_files = [
            'css/main.css',
            'js/main.js',
        ]

    def print_header(self, title):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title.center(60)}")
        print(f"{Fore.CYAN}{'='*60}")

    def print_success(self, message):
        print(f"{Fore.GREEN}✓ {message}")
        self.success_count += 1

    def print_warning(self, message):
        print(f"{Fore.YELLOW}⚠ {message}")
        self.warnings.append(message)

    def print_error(self, message):
        print(f"{Fore.RED}✗ {message}")
        self.errors.append(message)

    def check_templates(self):
        """Vérifier l'existence des templates"""
        self.print_header("Vérification des Templates")
        
        for template_name in self.required_templates:
            try:
                template = get_template(template_name)
                self.print_success(f"Template trouvé: {template_name}")
            except TemplateDoesNotExist:
                self.print_error(f"Template manquant: {template_name}")

    def check_static_files(self):
        """Vérifier l'existence des fichiers statiques"""
        self.print_header("Vérification des Fichiers Statiques")
        
        static_dir = Path(settings.STATICFILES_DIRS[0]) if settings.STATICFILES_DIRS else Path(settings.STATIC_ROOT)
        
        for static_file in self.required_static_files:
            file_path = static_dir / static_file
            if file_path.exists():
                self.print_success(f"Fichier statique trouvé: {static_file}")
            else:
                self.print_error(f"Fichier statique manquant: {static_file}")

    def check_urls(self):
        """Vérifier la configuration des URLs"""
        self.print_header("Vérification des URLs")
        
        for url_name, kwargs in self.urls_to_test:
            try:
                url = reverse(url_name, kwargs=kwargs)
                self.print_success(f"URL configurée: {url_name} -> {url}")
            except NoReverseMatch:
                self.print_error(f"URL non configurée: {url_name}")
        
        for url_name, kwargs in self.parameterized_urls:
            try:
                url = reverse(url_name, kwargs=kwargs)
                self.print_success(f"URL avec paramètres: {url_name} -> {url}")
            except NoReverseMatch:
                self.print_error(f"URL avec paramètres non configurée: {url_name}")

    def check_server_response(self):
        """Vérifier les réponses du serveur"""
        self.print_header("Test des Réponses Serveur")
        
        try:
            # Test de base
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                self.print_success(f"Serveur accessible: {self.base_url}")
            else:
                self.print_error(f"Serveur non accessible: {response.status_code}")
                return
        except requests.ConnectionError:
            self.print_error(f"Impossible de se connecter au serveur: {self.base_url}")
            return
        except requests.Timeout:
            self.print_error("Timeout lors de la connexion au serveur")
            return

        # Test des pages principales
        test_urls = [
            '/',
            '/login/',
            '/register/',
            '/dashboard/buyer/',
            '/dashboard/seller/',
            '/transactions/create/',
            '/kyc/status/',
        ]
        
        for url in test_urls:
            try:
                full_url = urljoin(self.base_url, url)
                response = requests.get(full_url, timeout=5)
                
                if response.status_code == 200:
                    self.print_success(f"Page accessible: {url}")
                elif response.status_code == 302:
                    self.print_warning(f"Redirection: {url} -> {response.headers.get('Location', 'Unknown')}")
                elif response.status_code == 404:
                    self.print_error(f"Page non trouvée: {url}")
                else:
                    self.print_warning(f"Réponse inattendue pour {url}: {response.status_code}")
                    
            except requests.RequestException as e:
                self.print_error(f"Erreur lors du test de {url}: {str(e)}")

    def check_css_js_loading(self):
        """Vérifier le chargement des CSS et JS"""
        self.print_header("Vérification CSS/JS")
        
        static_urls = [
            '/static/css/main.css',
            '/static/js/main.js',
        ]
        
        for url in static_urls:
            try:
                full_url = urljoin(self.base_url, url)
                response = requests.get(full_url, timeout=5)
                
                if response.status_code == 200:
                    self.print_success(f"Fichier statique accessible: {url}")
                else:
                    self.print_error(f"Fichier statique non accessible: {url} ({response.status_code})")
                    
            except requests.RequestException:
                self.print_error(f"Erreur lors du chargement de: {url}")

    def check_responsive_design(self):
        """Vérifier des éléments de design responsive"""
        self.print_header("Vérification Design Responsive")
        
        try:
            response = requests.get(self.base_url, timeout=5)
            content = response.text
            
            # Vérifier la présence du viewport meta tag
            if 'viewport' in content:
                self.print_success("Meta viewport trouvé")
            else:
                self.print_warning("Meta viewport manquant")
            
            # Vérifier Bootstrap
            if 'bootstrap' in content.lower():
                self.print_success("Bootstrap détecté")
            else:
                self.print_warning("Bootstrap non détecté")
            
            # Vérifier Bootstrap Icons
            if 'bootstrap-icons' in content:
                self.print_success("Bootstrap Icons détecté")
            else:
                self.print_warning("Bootstrap Icons non détecté")
                
        except requests.RequestException:
            self.print_error("Impossible de vérifier le design responsive")

    def check_security_headers(self):
        """Vérifier les headers de sécurité"""
        self.print_header("Vérification Sécurité")
        
        try:
            response = requests.get(self.base_url, timeout=5)
            headers = response.headers
            
            # Vérifier X-Frame-Options
            if 'X-Frame-Options' in headers:
                self.print_success("X-Frame-Options présent")
            else:
                self.print_warning("X-Frame-Options manquant")
            
            # Vérifier X-Content-Type-Options
            if 'X-Content-Type-Options' in headers:
                self.print_success("X-Content-Type-Options présent")
            else:
                self.print_warning("X-Content-Type-Options manquant")
                
        except requests.RequestException:
            self.print_error("Impossible de vérifier les headers de sécurité")

    def check_performance(self):
        """Vérifier les performances de base"""
        self.print_header("Test de Performance")
        
        try:
            start_time = time.time()
            response = requests.get(self.base_url, timeout=10)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response_time < 1.0:
                self.print_success(f"Temps de réponse excellent: {response_time:.2f}s")
            elif response_time < 2.0:
                self.print_success(f"Temps de réponse bon: {response_time:.2f}s")
            elif response_time < 5.0:
                self.print_warning(f"Temps de réponse acceptable: {response_time:.2f}s")
            else:
                self.print_error(f"Temps de réponse lent: {response_time:.2f}s")
                
        except requests.RequestException:
            self.print_error("Impossible de tester les performances")

    def run_all_checks(self):
        """Exécuter tous les tests"""
        print(f"{Fore.MAGENTA}{Style.BRIGHT}")
        print("🚀 KIMI ESCROW - Vérification Frontend")
        print("=====================================")
        
        self.check_templates()
        self.check_static_files()
        self.check_urls()
        self.check_server_response()
        self.check_css_js_loading()
        self.check_responsive_design()
        self.check_security_headers()
        self.check_performance()
        
        # Résumé
        self.print_header("Résumé des Tests")
        
        total_checks = self.success_count + len(self.warnings) + len(self.errors)
        
        print(f"{Fore.GREEN}✓ Succès: {self.success_count}")
        print(f"{Fore.YELLOW}⚠ Avertissements: {len(self.warnings)}")
        print(f"{Fore.RED}✗ Erreurs: {len(self.errors)}")
        print(f"{Fore.CYAN}📊 Total: {total_checks} vérifications")
        
        if self.errors:
            print(f"\n{Fore.RED}🚨 ERREURS CRITIQUES:")
            for error in self.errors[:5]:  # Afficher les 5 premières erreurs
                print(f"{Fore.RED}  • {error}")
            if len(self.errors) > 5:
                print(f"{Fore.RED}  • ... et {len(self.errors) - 5} autres erreurs")
                
        if self.warnings:
            print(f"\n{Fore.YELLOW}⚠️  AVERTISSEMENTS:")
            for warning in self.warnings[:5]:  # Afficher les 5 premiers avertissements
                print(f"{Fore.YELLOW}  • {warning}")
            if len(self.warnings) > 5:
                print(f"{Fore.YELLOW}  • ... et {len(self.warnings) - 5} autres avertissements")
        
        # Score final
        if len(self.errors) == 0:
            if len(self.warnings) == 0:
                print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 EXCELLENT! Frontend prêt pour la production!")
            else:
                print(f"\n{Fore.YELLOW}{Style.BRIGHT}👍 BON! Quelques améliorations recommandées.")
        else:
            print(f"\n{Fore.RED}{Style.BRIGHT}❌ ATTENTION! Des corrections sont nécessaires avant la production.")
        
        return len(self.errors) == 0


def main():
    """Point d'entrée principal"""
    checker = FrontendChecker()
    
    try:
        success = checker.run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Vérification interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}💥 Erreur inattendue: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
