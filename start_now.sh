#!/bin/bash
# Démarrage ultra-rapide Kimi Escrow

echo "⚡ Démarrage ultra-rapide Kimi Escrow"
echo "====================================="

# Copier la configuration minimale
if [ ! -f ".env" ]; then
    echo "📝 Copie de la configuration minimale..."
    cp env.minimal .env
fi

# Démarrer avec Docker Compose
echo "🚀 Démarrage des services..."
docker-compose up -d

# Attendre et vérifier
echo "⏳ Attente des services..."
sleep 15

echo "🔍 Vérification..."
docker-compose ps

echo ""
echo "🎉 Prêt!"
echo "📱 http://localhost:8003"
echo "👤 Admin: admin / admin123"
echo "🔧 Logs: docker-compose logs -f"
