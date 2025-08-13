#!/bin/bash
# Mise à jour avec possibilité de rollback

set -e

BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
ROLLBACK_FILE="rollback_$(date +%Y%m%d_%H%M%S).sh"

echo "🔄 Mise à jour avec rollback - PRODUCTION"
echo "=========================================="

# Créer le script de rollback
cat > $ROLLBACK_FILE << 'ROLLBACK_EOF'
#!/bin/bash
echo "🔄 Rollback en cours..."
docker-compose down
git reset --hard HEAD~1
docker-compose up -d
docker-compose exec -T db psql -U postgres kimi_escrow < $BACKUP_FILE
echo "✅ Rollback terminé"
ROLLBACK_EOF

chmod +x $ROLLBACK_FILE

# Sauvegarde
echo "💾 Sauvegarde..."
docker-compose exec db pg_dump -U postgres kimi_escrow > $BACKUP_FILE

# Mise à jour
echo "�� Mise à jour..."
git pull origin main
docker-compose build --no-cache
docker-compose up -d

# Test
echo "🧪 Test de l'application..."
sleep 30
if curl -f http://localhost:8003/api/core/health/ > /dev/null 2>&1; then
    echo "✅ Mise à jour réussie!"
    echo "�� Pour faire un rollback: ./$ROLLBACK_FILE"
else
    echo "❌ Mise à jour échouée!"
    echo "🔄 Lancement du rollback automatique..."
    ./$ROLLBACK_FILE
fi
