# Guide de Déploiement - Kimi Escrow Backend

## 🚀 Déploiement Rapide

### Option 1: Déploiement avec Docker (Recommandé)

#### Prérequis
- Docker installé
- Docker Compose installé
- Au moins 4GB de RAM disponible
- 10GB d'espace disque libre

#### Étapes de déploiement

1. **Configurer l'environnement**
   ```bash
   # Copier le fichier d'environnement
   cp env.production .env
   
   # Éditer les variables d'environnement
   nano .env
   ```

2. **Déployer l'application**
   ```bash
   # Déploiement complet
   ./deploy_production.sh
   
   # Ou avec nettoyage complet
   ./deploy_production.sh --clean
   ```

3. **Vérifier le déploiement**
   ```bash
   ./check_status.sh
   ```

#### Services disponibles après déploiement
- **Application web**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin/
- **API Swagger**: http://localhost:8000/swagger/
- **Base de données**: localhost:5434
- **Redis**: localhost:6379

### Option 2: Développement local

#### Prérequis
- Python 3.11+
- PostgreSQL
- Redis
- Environnement virtuel Python

#### Étapes de démarrage

1. **Démarrer les services de base**
   ```bash
   # PostgreSQL
   docker run --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=kimi_escrow -p 5432:5432 -d postgres:15
   
   # Redis
   docker run --name redis -p 6379:6379 -d redis:7-alpine
   ```

2. **Démarrer l'application**
   ```bash
   ./start_dev.sh
   ```

## 🔧 Configuration

### Variables d'environnement importantes

#### Base de données
```bash
DB_NAME=kimi_escrow
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost  # ou 'db' pour Docker
DB_PORT=5432
```

#### Redis
```bash
REDIS_URL=redis://localhost:6379/0  # ou redis://redis:6379/0 pour Docker
```

#### Sécurité
```bash
SECRET_KEY=your-super-secret-django-key
DEBUG=False  # Toujours False en production
ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip
```

### Configuration des services de paiement

#### MTN Mobile Money
```bash
MTN_MOMO_SUBSCRIPTION_KEY=your-mtn-subscription-key
MTN_MOMO_API_USER=your-mtn-api-user
MTN_MOMO_API_KEY=your-mtn-api-key
MTN_MOMO_ENVIRONMENT=sandbox  # ou 'production'
```

#### Orange Money
```bash
ORANGE_MONEY_CLIENT_ID=your-orange-client-id
ORANGE_MONEY_CLIENT_SECRET=your-orange-client-secret
ORANGE_MONEY_ENVIRONMENT=sandbox  # ou 'production'
```

## 📊 Monitoring et Maintenance

### Commandes utiles

#### Vérifier l'état des services
```bash
./check_status.sh
```

#### Voir les logs
```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f db
```

#### Redémarrer un service
```bash
docker-compose restart web
docker-compose restart celery
```

#### Arrêter tous les services
```bash
docker-compose down
```

#### Nettoyer complètement
```bash
docker-compose down -v --remove-orphans
docker system prune -f
```

### Sauvegarde et restauration

#### Sauvegarder la base de données
```bash
docker-compose exec db pg_dump -U postgres kimi_escrow > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Restaurer la base de données
```bash
docker-compose exec -T db psql -U postgres kimi_escrow < backup_file.sql
```

## 🚨 Dépannage

### Problèmes courants

#### L'application ne démarre pas
1. Vérifier les logs: `docker-compose logs web`
2. Vérifier que PostgreSQL et Redis sont accessibles
3. Vérifier les variables d'environnement

#### Erreurs de base de données
1. Vérifier que PostgreSQL est en cours d'exécution
2. Vérifier les paramètres de connexion
3. Appliquer les migrations: `docker-compose exec web python manage.py migrate`

#### Erreurs Redis
1. Vérifier que Redis est en cours d'exécution
2. Vérifier l'URL Redis dans les variables d'environnement

#### Problèmes de permissions
```bash
# Donner les bonnes permissions aux scripts
chmod +x *.sh

# Vérifier les permissions des volumes Docker
sudo chown -R $USER:$USER ./logs ./media ./staticfiles
```

### Logs et debugging

#### Activer le mode debug temporairement
```bash
# Dans le fichier .env
DEBUG=True

# Redémarrer le service
docker-compose restart web
```

#### Vérifier la santé de l'API
```bash
curl http://localhost:8000/api/core/health/
```

## 🔒 Sécurité

### Recommandations de production

1. **Changer tous les mots de passe par défaut**
2. **Utiliser des clés secrètes fortes**
3. **Configurer HTTPS avec des certificats SSL valides**
4. **Restreindre l'accès aux ports sensibles**
5. **Configurer un pare-feu**
6. **Mettre en place des sauvegardes automatiques**

### Variables sensibles à changer absolument
- `SECRET_KEY`
- `DB_PASSWORD`
- `FIELD_ENCRYPTION_KEY`
- Toutes les clés API des services de paiement

## 📞 Support

En cas de problème:
1. Vérifier les logs avec `./check_status.sh`
2. Consulter la documentation Django
3. Vérifier la configuration Docker
4. Contacter l'équipe de développement

---

**Note**: Ce guide est destiné au serveur de développement. Pour la production, des configurations supplémentaires de sécurité et de performance sont nécessaires.
