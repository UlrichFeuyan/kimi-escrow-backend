#!/usr/bin/env python3
"""
Test de l'API de réinitialisation de mot de passe
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/auth"

def test_password_reset_request():
    """Tester la demande de réinitialisation de mot de passe"""
    print("🔐 Test de la demande de réinitialisation de mot de passe...")
    
    url = f"{API_BASE}/password-reset/request/"
    data = {
        "email": "test@example.com"  # Remplacez par un email valide
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Demande de réinitialisation réussie")
        else:
            print("❌ Échec de la demande de réinitialisation")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("-" * 50)

def test_password_reset_confirm():
    """Tester la confirmation de réinitialisation de mot de passe"""
    print("🔑 Test de la confirmation de réinitialisation de mot de passe...")
    
    url = f"{API_BASE}/password-reset/confirm/"
    data = {
        "email": "test@example.com",  # Remplacez par un email valide
        "reset_code": "123456",       # Remplacez par le code reçu
        "new_password": "NewPassword123!"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Confirmation de réinitialisation réussie")
        else:
            print("❌ Échec de la confirmation de réinitialisation")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("-" * 50)

def test_api_documentation():
    """Tester l'accès à la documentation de l'API"""
    print("📚 Test de l'accès à la documentation de l'API...")
    
    urls = [
        f"{BASE_URL}/swagger/",
        f"{BASE_URL}/redoc/",
        f"{BASE_URL}/api/auth/"
    ]
    
    for url in urls:
        try:
            response = requests.get(url)
            print(f"{url}: {response.status_code}")
        except Exception as e:
            print(f"{url}: Erreur - {e}")
    
    print("-" * 50)

if __name__ == "__main__":
    print("🚀 Tests de l'API de réinitialisation de mot de passe")
    print("=" * 50)
    
    # Test de la documentation
    test_api_documentation()
    
    # Tests de l'API (nécessitent un serveur en cours d'exécution)
    print("\n⚠️  Les tests suivants nécessitent un serveur Django en cours d'exécution")
    print("   Démarrez le serveur avec: python manage.py runserver")
    print("=" * 50)
    
    test_password_reset_request()
    test_password_reset_confirm()
    
    print("\n✨ Tests terminés !")
