#!/usr/bin/env python3
"""
Script de diagnostic des templates Django
"""

import os
import sys
import django
from pathlib import Path

# Configuration Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')

django.setup()

from django.template.loader import get_template
from django.template import Template, TemplateSyntaxError

def check_template(template_name):
    """Vérifier un template spécifique"""
    try:
        template = get_template(template_name)
        print(f"✅ {template_name}: OK")
        return True
    except TemplateSyntaxError as e:
        print(f"❌ {template_name}: Erreur de syntaxe - {e}")
        return False
    except Exception as e:
        print(f"❌ {template_name}: Erreur - {e}")
        return False

def check_all_templates():
    """Vérifier tous les templates principaux"""
    templates_to_check = [
        'base.html',
        'home.html',
        'includes/header.html',
        'includes/navbar_buyer.html',
        'includes/navbar_seller.html',
        'includes/navbar_arbitre.html',
        'includes/navbar_admin.html',
        'includes/footer.html',
    ]
    
    print("🔍 Vérification des templates...")
    print("=" * 50)
    
    results = []
    for template in templates_to_check:
        result = check_template(template)
        results.append((template, result))
    
    print("\n📊 Résumé:")
    print("=" * 50)
    successful = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Templates vérifiés: {total}")
    print(f"✅ Succès: {successful}")
    print(f"❌ Échecs: {total - successful}")
    
    if successful == total:
        print("\n🎉 Tous les templates sont valides!")
    else:
        print("\n⚠️  Certains templates ont des problèmes.")
        print("\nTemplates problématiques:")
        for template, result in results:
            if not result:
                print(f"  - {template}")

def check_static_tag_usage():
    """Vérifier l'utilisation du tag static dans les templates"""
    print("\n🔍 Vérification de l'utilisation du tag static...")
    print("=" * 50)
    
    templates_dir = BASE_DIR / 'templates'
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(templates_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Vérifier si le template utilise {% static %}
                    if '{% static' in content:
                        # Vérifier si {% load static %} est présent
                        if '{% load static %}' in content:
                            print(f"✅ {relative_path}: Utilise static et charge static")
                        else:
                            print(f"⚠️  {relative_path}: Utilise static mais ne charge pas static")
                    
                except Exception as e:
                    print(f"❌ {relative_path}: Erreur de lecture - {e}")

if __name__ == '__main__':
    print("🚀 Diagnostic des templates Django")
    print("=" * 50)
    
    check_all_templates()
    check_static_tag_usage()
    
    print("\n✨ Diagnostic terminé!")
