#!/bin/bash
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
