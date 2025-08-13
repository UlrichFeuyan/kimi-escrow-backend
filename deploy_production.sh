#!/bin/bash
# Script de déploiement Kimi Escrow - PRODUCTION
# Utilise Docker Compose pour un déploiement complet

set -e

echo "🚀 Déploiement Kimi Escrow - PRODUCTION"
echo "========================================"

# Vérifier que Docker et Docker Compose sont installés
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Vérifier que le fichier d'environnement existe
if [ ! -f "env.production" ]; then
    echo "❌ Le fichier env.production n'existe pas."
    echo "Veuillez créer ce fichier avec vos paramètres de production."
    exit 1
fi

# Arrêter les services existants
echo "🛑 Arrêt des services existants..."
docker-compose down --remove-orphans

# Nettoyer les images et volumes si nécessaire
if [ "$1" = "--clean" ]; then
    echo "🧹 Nettoyage complet..."
    docker-compose down -v --remove-orphans
    docker system prune -f
fi

# Construire les images
echo "🔨 Construction des images Docker..."
docker-compose build --no-cache

# Démarrer les services
echo "🚀 Démarrage des services..."
docker-compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente que les services soient prêts..."
sleep 30

# Vérifier l'état des services
echo "🔍 Vérification de l'état des services..."
docker-compose ps

# Vérifier les logs
echo "📋 Logs des services:"
docker-compose logs --tail=20

# Vérifier la santé de l'application
echo "🏥 Vérification de la santé de l'application..."
if curl -f http://localhost:8000/api/core/health/ > /dev/null 2>&1; then
    echo "✅ Application en ligne et accessible!"
else
    echo "⚠️  L'application n'est pas encore accessible, attendez quelques secondes..."
    echo "Vous pouvez vérifier les logs avec: docker-compose logs -f web"
fi

echo ""
echo "🎉 Déploiement terminé!"
echo ""
echo "📱 Services disponibles:"
echo "   - Application web: http://localhost:8000"
echo "   - Admin Django: http://localhost:8000/admin/"
echo "   - API Swagger: http://localhost:8000/swagger/"
echo "   - Base de données: localhost:5434"
echo "   - Redis: localhost:6381"
echo ""
echo "🔧 Commandes utiles:"
echo "   - Voir les logs: docker-compose logs -f [service]"
echo "   - Arrêter: docker-compose down"
echo "   - Redémarrer: docker-compose restart"
echo "   - Nettoyer: ./deploy_production.sh --clean"
