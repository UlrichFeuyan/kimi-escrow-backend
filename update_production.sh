#!/bin/bash
# Script de mise à jour automatique en production

echo "🔄 Mise à jour Kimi Escrow - PRODUCTION"
echo "========================================"

# Sauvegarder la base de données
echo "💾 Sauvegarde de la base de données..."
docker-compose exec db pg_dump -U postgres kimi_escrow > backup_$(date +%Y%m%d_%H%M%S).sql

# Arrêter les services
echo "�� Arrêt des services..."
docker-compose down

# Récupérer les dernières modifications
echo "📥 Récupération des modifications..."
git pull origin main  # ou votre branche principale

# Reconstruire les images
echo "�� Reconstruction des images..."
docker-compose build --no-cache

# Redémarrer les services
echo "🚀 Redémarrage des services..."
docker-compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente des services..."
sleep 30

# Appliquer les migrations si nécessaire
echo "🗄️  Application des migrations..."
docker-compose exec web python manage.py migrate

# Collecter les fichiers statiques
echo "📁 Collection des fichiers statiques..."
docker-compose exec web python manage.py collectstatic --noinput

# Vérifier l'état
echo "�� Vérification de l'état..."
docker-compose ps

echo "✅ Mise à jour terminée!"
echo "📱 Application: http://localhost:8003"
