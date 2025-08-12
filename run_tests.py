#!/usr/bin/env python
"""
Script pour exécuter tous les tests de l'API Kimi Escrow
Génère un rapport détaillé des résultats de tests
"""

import os
import sys
import django
import subprocess
import time
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr


def setup_django():
    """Configurer Django pour les tests"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimi_escrow.settings')
    django.setup()


def run_test_suite(test_module, description):
    """Exécuter une suite de tests spécifique"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTS: {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Exécuter les tests avec manage.py
        result = subprocess.run([
            sys.executable, 'manage.py', 'test', test_module,
            '--verbosity=2',
            '--keepdb',
            '--parallel'
        ], capture_output=True, text=True, timeout=300)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} - RÉUSSI ({duration:.2f}s)")
            success = True
        else:
            print(f"❌ {description} - ÉCHEC ({duration:.2f}s)")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            success = False
            
        return {
            'module': test_module,
            'description': description,
            'success': success,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT (>300s)")
        return {
            'module': test_module,
            'description': description,
            'success': False,
            'duration': 300,
            'stdout': '',
            'stderr': 'Test timeout after 300 seconds'
        }
    except Exception as e:
        print(f"💥 {description} - ERREUR: {str(e)}")
        return {
            'module': test_module,
            'description': description,
            'success': False,
            'duration': 0,
            'stdout': '',
            'stderr': str(e)
        }


def run_coverage_analysis():
    """Exécuter l'analyse de couverture de code"""
    print(f"\n{'='*60}")
    print("📊 ANALYSE DE COUVERTURE")
    print(f"{'='*60}")
    
    try:
        # Installer coverage si nécessaire
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'coverage'], 
                      capture_output=True)
        
        # Exécuter les tests avec coverage
        subprocess.run([
            'coverage', 'run', '--source=.', 'manage.py', 'test',
            '--keepdb'
        ], capture_output=True)
        
        # Générer le rapport
        result = subprocess.run(['coverage', 'report'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Analyse de couverture terminée")
            print("\nRAPPORT DE COUVERTURE:")
            print(result.stdout)
            
            # Sauvegarder le rapport HTML
            subprocess.run(['coverage', 'html'], capture_output=True)
            print("📄 Rapport HTML généré dans htmlcov/")
            
            return True
        else:
            print("❌ Erreur dans l'analyse de couverture")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"💥 Erreur dans l'analyse de couverture: {str(e)}")
        return False


def check_code_quality():
    """Vérifier la qualité du code avec flake8 et autres outils"""
    print(f"\n{'='*60}")
    print("🔍 VÉRIFICATION DE LA QUALITÉ DU CODE")
    print(f"{'='*60}")
    
    quality_checks = []
    
    try:
        # Installer les outils si nécessaire
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'flake8', 'black', 'isort'], 
                      capture_output=True)
        
        # Flake8 - Style et erreurs
        print("📋 Vérification avec flake8...")
        result = subprocess.run(['flake8', '.', '--max-line-length=100', 
                               '--exclude=venv,migrations,staticfiles'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Flake8 - Aucune erreur trouvée")
            quality_checks.append(("Flake8", True, ""))
        else:
            print("⚠️ Flake8 - Problèmes détectés:")
            print(result.stdout)
            quality_checks.append(("Flake8", False, result.stdout))
        
        # Black - Formatage
        print("\n🎨 Vérification du formatage avec Black...")
        result = subprocess.run(['black', '--check', '.', '--exclude=venv|migrations|staticfiles'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Black - Code bien formaté")
            quality_checks.append(("Black", True, ""))
        else:
            print("⚠️ Black - Formatage à corriger:")
            print(result.stdout)
            quality_checks.append(("Black", False, result.stdout))
        
        # isort - Imports
        print("\n📦 Vérification des imports avec isort...")
        result = subprocess.run(['isort', '--check-only', '.', '--skip=venv'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ isort - Imports bien organisés")
            quality_checks.append(("isort", True, ""))
        else:
            print("⚠️ isort - Organisation des imports à corriger:")
            print(result.stdout)
            quality_checks.append(("isort", False, result.stdout))
            
    except Exception as e:
        print(f"💥 Erreur dans la vérification de qualité: {str(e)}")
        quality_checks.append(("Error", False, str(e)))
    
    return quality_checks


def generate_report(test_results, quality_checks, coverage_success):
    """Générer un rapport complet des tests"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Compter les succès et échecs
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results if result['success'])
    failed_tests = total_tests - successful_tests
    total_duration = sum(result['duration'] for result in test_results)
    
    # Générer le rapport
    report = f"""
# 📋 RAPPORT DE TESTS - KIMI ESCROW API
**Généré le:** {timestamp}

## 📊 RÉSUMÉ EXÉCUTIF
- **Tests exécutés:** {total_tests}
- **Succès:** {successful_tests} ✅
- **Échecs:** {failed_tests} ❌ 
- **Taux de réussite:** {(successful_tests/total_tests*100):.1f}%
- **Durée totale:** {total_duration:.2f} secondes

## 📝 DÉTAIL DES TESTS

"""

    for result in test_results:
        status_icon = "✅" if result['success'] else "❌"
        report += f"""
### {status_icon} {result['description']}
- **Module:** `{result['module']}`
- **Durée:** {result['duration']:.2f}s
- **Statut:** {'RÉUSSI' if result['success'] else 'ÉCHEC'}
"""
        if not result['success'] and result['stderr']:
            report += f"- **Erreur:** ```{result['stderr'][:200]}...```\n"

    # Ajouter la section qualité du code
    report += f"""

## 🔍 QUALITÉ DU CODE

"""
    
    for tool, success, output in quality_checks:
        status_icon = "✅" if success else "⚠️"
        report += f"- **{tool}:** {status_icon} {'RÉUSSI' if success else 'À CORRIGER'}\n"
    
    # Ajouter la section couverture
    coverage_icon = "✅" if coverage_success else "❌"
    report += f"""

## 📊 COUVERTURE DE CODE
- **Analyse:** {coverage_icon} {'RÉUSSIE' if coverage_success else 'ÉCHEC'}
"""
    if coverage_success:
        report += "- **Rapport HTML:** Disponible dans `htmlcov/index.html`\n"

    # Recommandations
    report += f"""

## 🎯 RECOMMANDATIONS

"""
    
    if failed_tests > 0:
        report += f"- ⚠️ **{failed_tests} test(s) en échec** - À corriger en priorité\n"
    
    if not all(success for _, success, _ in quality_checks):
        report += "- 🔧 **Qualité du code** - Corriger les problèmes détectés par les outils de linting\n"
    
    if not coverage_success:
        report += "- 📊 **Couverture de code** - Configurer et exécuter l'analyse de couverture\n"
    
    if successful_tests == total_tests:
        report += "- 🎉 **Excellent !** Tous les tests passent. Continuez le bon travail !\n"

    # Sauvegarder le rapport
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Rapport sauvegardé dans: {report_file}")
    
    return report


def main():
    """Fonction principale"""
    print("🚀 LANCEMENT DE LA SUITE DE TESTS KIMI ESCROW")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration Django
    setup_django()
    
    # Définir les suites de tests
    test_suites = [
        ('users.tests', 'Tests d\'authentification et utilisateurs'),
        ('escrow.tests', 'Tests des transactions escrow'),
        ('payments.tests', 'Tests des paiements Mobile Money'),
        ('disputes.tests', 'Tests du système de litiges'),
        ('core.tests', 'Tests des fonctionnalités core'),
        ('test_integration', 'Tests d\'intégration end-to-end'),
    ]
    
    # Exécuter tous les tests
    print(f"\n🔥 Exécution de {len(test_suites)} suites de tests...")
    test_results = []
    
    for test_module, description in test_suites:
        result = run_test_suite(test_module, description)
        test_results.append(result)
    
    # Vérification de la qualité du code
    quality_checks = check_code_quality()
    
    # Analyse de couverture
    coverage_success = run_coverage_analysis()
    
    # Génération du rapport
    print(f"\n{'='*60}")
    print("📋 GÉNÉRATION DU RAPPORT")
    print(f"{'='*60}")
    
    report = generate_report(test_results, quality_checks, coverage_success)
    
    # Affichage du résumé final
    successful_tests = sum(1 for result in test_results if result['success'])
    total_tests = len(test_results)
    
    print(f"\n{'='*60}")
    print("🎯 RÉSUMÉ FINAL")
    print(f"{'='*60}")
    print(f"Tests réussis: {successful_tests}/{total_tests}")
    print(f"Taux de réussite: {(successful_tests/total_tests*100):.1f}%")
    
    if successful_tests == total_tests:
        print("🎉 TOUS LES TESTS SONT PASSÉS ! 🎉")
        return True
    else:
        print(f"❌ {total_tests - successful_tests} test(s) en échec")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
