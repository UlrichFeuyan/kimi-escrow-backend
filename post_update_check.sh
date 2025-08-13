#!/bin/bash
echo "🔍 Vérification post-mise à jour..."
echo "==================================="

# Attendre que les services soient prêts
sleep 30

# Vérifier l'état des services
echo "�� État des services:"
docker-compose ps

# Vérifier la santé de l'application
echo "🏥 Santé de l'application:"
curl -f http://localhost:8003/api/core/health/ && echo "✅ OK" || echo "❌ KO"

# Vérifier les migrations
echo "🗄️  État des migrations:"
docker-compose exec web python manage.py showmigrations

# Vérifier les logs
echo "📋 Logs récents:"
docker-compose logs --tail=10
