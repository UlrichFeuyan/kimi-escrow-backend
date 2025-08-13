#!/bin/bash
echo "�� Vérification pré-mise à jour..."
echo "=================================="

# Vérifier l'espace disque
echo "�� Espace disque:"
df -h | grep -E '^/dev/'

# Vérifier la mémoire
echo "🧠 Mémoire:"
free -h

# Vérifier les services
echo "🚀 Services:"
docker-compose ps

# Vérifier les logs d'erreur
echo "📋 Logs d'erreur récents:"
docker-compose logs --tail=10 | grep -i error

# Vérifier la santé de l'application
echo "🏥 Santé de l'application:"
curl -f http://localhost:8003/api/core/health/ && echo "✅ OK" || echo "❌ KO"
