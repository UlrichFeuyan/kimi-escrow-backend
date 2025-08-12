#!/bin/bash
# Déploiement rapide Kimi Escrow - Version simple

echo "🚀 Déploiement rapide Kimi Escrow"
echo "=================================="

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

# Arrêter les services existants
echo "🛑 Arrêt des services existants..."
docker-compose down --remove-orphans 2>/dev/null || true

# Démarrer les services
echo "🚀 Démarrage des services..."
docker-compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente des services..."
sleep 20

# Vérifier l'état
echo "🔍 État des services:"
docker-compose ps

echo ""
echo "🎉 Déploiement terminé!"
echo "📱 Application: http://localhost:8000"
echo "🔧 Logs: docker-compose logs -f"
