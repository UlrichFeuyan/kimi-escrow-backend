#!/bin/bash

# Script de démarrage du serveur Kimi Escrow avec frontend

echo "🚀 Démarrage du serveur Kimi Escrow..."

# Activer l'environnement virtuel
source venv/bin/activate

# Appliquer les migrations si nécessaire
echo "📝 Vérification des migrations..."
python manage.py migrate --no-input

# Collecter les fichiers statiques
echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --no-input --clear

# Démarrer le serveur
echo "🌐 Démarrage du serveur sur http://localhost:8000/"
echo ""
echo "📍 URLs disponibles:"
echo "   🏠 Frontend:        http://localhost:8000/"
echo "   📋 API Swagger:     http://localhost:8000/swagger/"
echo "   ⚙️  Admin Django:    http://localhost:8000/admin/"
echo ""
python manage.py runserver 0.0.0.0:8000
