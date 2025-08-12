#!/bin/bash
# Script de démarrage rapide pour le développement
# Utilise l'environnement virtuel Python local

set -e

echo "🚀 Démarrage Kimi Escrow - DÉVELOPPEMENT"
echo "========================================="

# Vérifier que l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer/mettre à jour les dépendances
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

# Vérifier que PostgreSQL est en cours d'exécution
echo "🗄️  Vérification de PostgreSQL..."
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL n'est pas accessible sur localhost:5432"
    echo "Veuillez démarrer PostgreSQL ou utiliser Docker:"
    echo "docker run --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=kimi_escrow -p 5432:5432 -d postgres:15"
    echo ""
    read -p "Voulez-vous continuer sans PostgreSQL? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Vérifier que Redis est en cours d'exécution
echo "🔴 Vérification de Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis n'est pas accessible sur localhost:6379"
    echo "Veuillez démarrer Redis ou utiliser Docker:"
    echo "docker run --name redis -p 6379:6379 -d redis:7-alpine"
    echo ""
    read -p "Voulez-vous continuer sans Redis? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Appliquer les migrations
echo "🗄️  Application des migrations..."
python manage.py migrate

# Collecter les fichiers statiques
echo "📁 Collection des fichiers statiques..."
python manage.py collectstatic --noinput

# Créer un superutilisateur si nécessaire
echo "👤 Vérification du superutilisateur..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Création d\'un superutilisateur par défaut...')
    User.objects.create_superuser(
        phone_number='admin',
        password='admin123',
        first_name='Admin',
        last_name='System'
    )
    print('Superutilisateur créé: phone=admin, password=admin123')
else:
    print('Superutilisateur existe déjà')
"

# Démarrer l'application
echo "🌐 Démarrage de l'application..."
echo ""
echo "📱 Services disponibles:"
echo "   - Application web: http://localhost:8000"
echo "   - Admin Django: http://localhost:8000/admin/"
echo "   - API Swagger: http://localhost:8000/swagger/"
echo ""
echo "👤 Connexion admin:"
echo "   - Téléphone: admin"
echo "   - Mot de passe: admin123"
echo ""
echo "🛑 Pour arrêter: Ctrl+C"
echo ""

python manage.py runserver 0.0.0.0:8000
