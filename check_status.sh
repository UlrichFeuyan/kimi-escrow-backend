#!/bin/bash
# Script de vérification de l'état des services Kimi Escrow

echo "🔍 Vérification de l'état des services Kimi Escrow"
echo "================================================="

# Vérifier Docker
echo ""
echo "🐳 État de Docker:"
if command -v docker &> /dev/null; then
    echo "✅ Docker est installé"
    docker --version
else
    echo "❌ Docker n'est pas installé"
    exit 1
fi

# Vérifier Docker Compose
echo ""
echo "📦 État de Docker Compose:"
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose est installé"
    docker-compose --version
else
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

# Vérifier les services en cours d'exécution
echo ""
echo "🚀 Services en cours d'exécution:"
if [ -f "docker-compose.yml" ]; then
    docker-compose ps
else
    echo "⚠️  Fichier docker-compose.yml non trouvé"
fi

# Vérifier les ports
echo ""
echo "🔌 Vérification des ports:"
echo "Port 8003 (Application):"
if netstat -tuln | grep ":8003 " > /dev/null; then
    echo "✅ Port 8003 ouvert"
else
    echo "❌ Port 8003 fermé"
fi

echo "Port 5435 (PostgreSQL):"
if netstat -tuln | grep ":5435 " > /dev/null; then
    echo "✅ Port 5435 ouvert"
else
    echo "❌ Port 5435 fermé"
fi

echo "Port 6380 (Redis):"
if netstat -tuln | grep ":6380 " > /dev/null; then
    echo "✅ Port 6380 ouvert"
else
    echo "❌ Port 6380 fermé"
fi

echo "Port 80 (Nginx):"
if netstat -tuln | grep ":80 " > /dev/null; then
    echo "✅ Port 80 ouvert"
else
    echo "❌ Port 80 fermé"
fi

# Vérifier la santé de l'application
echo ""
echo "🏥 Vérification de la santé de l'application:"
if command -v curl &> /dev/null; then
    if curl -f http://localhost:8003/api/core/health/ > /dev/null 2>&1; then
        echo "✅ Application accessible sur http://localhost:8003"
        
        # Test de l'API
        echo "📡 Test de l'API:"
        response=$(curl -s http://localhost:8003/api/core/health/)
        echo "Réponse: $response"
    else
        echo "❌ Application non accessible sur http://localhost:8003"
    fi
else
    echo "⚠️  curl n'est pas installé, impossible de tester l'API"
fi

# Vérifier les logs récents
echo ""
echo "📋 Logs récents (dernières 10 lignes):"
if [ -f "docker-compose.yml" ]; then
    docker-compose logs --tail=10
else
    echo "⚠️  Impossible de récupérer les logs (docker-compose.yml non trouvé)"
fi

# Vérifier l'espace disque
echo ""
echo "💾 Espace disque:"
df -h | grep -E '^/dev/'

# Vérifier la mémoire
echo ""
echo "🧠 Utilisation de la mémoire:"
free -h

echo ""
echo "🔍 Vérification terminée!"
