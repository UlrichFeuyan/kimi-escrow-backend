# Kimi Escrow Backend

Backend complet pour une application de paiement escrow sécurisée au Cameroun, intégrant Mobile Money (MTN & Orange), vérification KYC avec Smile ID, et système d'arbitrage.

## 🚀 Fonctionnalités

- **Authentification JWT** avec django-rest-framework-simplejwt
- **Système de rôles RBAC** (BUYER, SELLER, ARBITRE, ADMIN)
- **Vérification KYC** avec intégration Smile ID (Cameroun)
- **Intégration Mobile Money** (MTN Mobile Money & Orange Money)
- **Transactions Escrow** avec jalons et preuves de livraison
- **Système de litiges** avec arbitrage
- **Audit trail** complet avec middleware personnalisé
- **Tâches asynchrones** avec Celery + Redis
- **API RESTful** complète avec documentation
- **Tests unitaires** et d'intégration
- **Déploiement Docker** prêt pour la production

## 📋 Prérequis

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (optionnel)

## 🛠️ Installation

### 1. Cloner le projet

```bash
git clone <repository-url>
cd kimi-escrow-backend
```

### 2. Créer l'environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration des variables d'environnement

```bash
cp env.example .env
```

Modifiez le fichier `.env` avec vos configurations :

```env
# Django Configuration
SECRET_KEY=your-super-secret-django-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DB_NAME=kimi_escrow
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6381/0

# Smile ID Configuration (Cameroon)
SMILE_ID_PARTNER_ID=your-smile-id-partner-id
SMILE_ID_API_KEY=your-smile-id-api-key
SMILE_ID_SANDBOX=True

# MTN Mobile Money Configuration
MTN_MOMO_SUBSCRIPTION_KEY=your-mtn-subscription-key
MTN_MOMO_API_USER=your-mtn-api-user
MTN_MOMO_API_KEY=your-mtn-api-key
MTN_MOMO_ENVIRONMENT=sandbox

# Orange Money Configuration
ORANGE_MONEY_CLIENT_ID=your-orange-client-id
ORANGE_MONEY_CLIENT_SECRET=your-orange-client-secret
ORANGE_MONEY_ENVIRONMENT=sandbox
```

### 5. Configuration de la base de données

```bash
# Créer la base de données PostgreSQL
createdb kimi_escrow

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser
```

### 6. Collecter les fichiers statiques

```bash
python manage.py collectstatic
```

## 🐳 Déploiement avec Docker

### Développement

```bash
# Construire et démarrer les services
docker-compose -f docker-compose.yml up --build

# En arrière-plan
docker-compose -f docker-compose.yml up -d --build
```

### Production

```bash
# Configurer les variables d'environnement de production
cp env.example .env.prod

# Démarrer en production
docker-compose -f docker-compose.yml up -d --build
```

## 🚀 Démarrage

### Mode développement

```bash
# Terminal 1 - Django
python manage.py runserver

# Terminal 2 - Celery Worker
celery -A kimi_escrow worker --loglevel=info

# Terminal 3 - Celery Beat (tâches programmées)
celery -A kimi_escrow beat --loglevel=info
```

### Mode production

```bash
# Avec Gunicorn
gunicorn kimi_escrow.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## 📚 Documentation API

### Endpoints d'authentification

#### Inscription
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+237612345678",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePassword123!",
    "password_confirmation": "SecurePassword123!",
    "role": "BUYER"
  }'
```

#### Connexion
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+237612345678",
    "password": "SecurePassword123!"
  }'
```

#### Vérification SMS
```bash
curl -X POST http://localhost:8000/api/auth/verify-phone/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "verification_code": "123456"
  }'
```

### Endpoints KYC

#### Upload de document
```bash
curl -X POST http://localhost:8000/api/auth/kyc/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "document_type=ID_FRONT" \
  -F "file=@/path/to/id_front.jpg"
```

#### Statut KYC
```bash
curl -X GET http://localhost:8000/api/auth/kyc/status/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Endpoints Escrow

#### Créer une transaction
```bash
curl -X POST http://localhost:8000/api/escrow/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "Vente iPhone 13",
    "description": "iPhone 13 Pro Max 256GB, état neuf",
    "category": "GOODS",
    "amount": 450000,
    "seller_phone": "+237698765432",
    "payment_deadline": "2024-01-15T23:59:59Z",
    "delivery_deadline": "2024-01-20T23:59:59Z",
    "delivery_address": "Douala, Cameroun"
  }'
```

#### Lister les transactions
```bash
curl -X GET http://localhost:8000/api/escrow/transactions/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Détail d'une transaction
```bash
curl -X GET http://localhost:8000/api/escrow/transactions/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Actions sur transaction
```bash
# Marquer comme livré (vendeur)
curl -X POST http://localhost:8000/api/escrow/transactions/1/actions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "action": "mark_delivered",
    "notes": "Colis livré à l'adresse indiquée"
  }'

# Confirmer la livraison (acheteur)
curl -X POST http://localhost:8000/api/escrow/transactions/1/actions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "action": "confirm_delivery",
    "notes": "Produit conforme, satisfait"
  }'

# Annuler la transaction
curl -X POST http://localhost:8000/api/escrow/transactions/1/actions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "action": "cancel",
    "notes": "Changement d'avis"
  }'
```

### Endpoints Paiements

#### Initier un paiement Mobile Money
```bash
curl -X POST http://localhost:8000/api/payments/momo/collect/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "transaction_id": 1,
    "phone_number": "+237612345678",
    "provider": "MTN_MOMO",
    "amount": 450000
  }'
```

#### Statut d'un paiement
```bash
curl -X GET http://localhost:8000/api/payments/status/PAY-ABC123/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Endpoints Administration

#### Statistiques utilisateurs (Admin)
```bash
curl -X GET http://localhost:8000/api/auth/admin/statistics/ \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

#### Approuver KYC (Admin)
```bash
curl -X POST http://localhost:8000/api/auth/admin/kyc/1/approve/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -d '{
    "action": "approve"
  }'
```

## 🔧 Configuration des APIs externes

### Smile ID (Cameroun)

1. Créer un compte sur [Smile ID](https://usesmileid.com/)
2. Obtenir votre Partner ID et API Key
3. Configurer les variables d'environnement :
   ```env
   SMILE_ID_PARTNER_ID=your_partner_id
   SMILE_ID_API_KEY=your_api_key
   SMILE_ID_SANDBOX=True
   ```

### MTN Mobile Money

1. S'inscrire sur [MTN Developer Portal](https://momodeveloper.mtn.com/)
2. Créer une application et obtenir les clés
3. Configurer les variables :
   ```env
   MTN_MOMO_SUBSCRIPTION_KEY=your_subscription_key
   MTN_MOMO_API_USER=your_api_user
   MTN_MOMO_API_KEY=your_api_key
   ```

### Orange Money

1. Contacter Orange Cameroun pour l'accès API
2. Obtenir les identifiants client
3. Configurer les variables :
   ```env
   ORANGE_MONEY_CLIENT_ID=your_client_id
   ORANGE_MONEY_CLIENT_SECRET=your_client_secret
   ```

## 🧪 Tests

### Exécuter tous les tests
```bash
python manage.py test
```

### Tests avec coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Génère un rapport HTML
```

### Tests spécifiques
```bash
# Tests d'une app
python manage.py test users

# Tests d'un module
python manage.py test users.tests.test_authentication

# Tests avec pattern
python manage.py test --pattern="test_*"
```

## 📊 Monitoring et Logs

### Logs de l'application
```bash
# Voir les logs en temps réel
tail -f logs/django.log

# Logs avec niveau de détail
python manage.py runserver --verbosity=2
```

### Monitoring Celery
```bash
# Monitoring des workers
celery -A kimi_escrow inspect active

# Statistiques des tâches
celery -A kimi_escrow inspect stats

# Interface web (optionnel)
pip install flower
celery -A kimi_escrow flower
```

## 🔒 Sécurité

### Variables d'environnement critiques à changer en production

```env
SECRET_KEY=                    # Clé Django unique et complexe
DEBUG=False                    # Désactiver le mode debug
FIELD_ENCRYPTION_KEY=          # Clé de chiffrement des données sensibles
DB_PASSWORD=                   # Mot de passe base de données sécurisé
```

### Configuration HTTPS en production

1. Obtenir un certificat SSL (Let's Encrypt recommandé)
2. Configurer Nginx avec SSL
3. Activer les paramètres de sécurité Django :
   ```python
   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   ```

## 🚨 Dépannage

### Erreurs courantes

#### Erreur de connexion à la base de données
```bash
# Vérifier que PostgreSQL est démarré
sudo systemctl status postgresql

# Vérifier la connexion
psql -h localhost -U postgres -d kimi_escrow
```

#### Erreur Redis
```bash
# Vérifier que Redis est démarré
sudo systemctl status redis

# Tester la connexion
redis-cli ping
```

#### Erreur de migration
```bash
# Réinitialiser les migrations (développement seulement)
python manage.py migrate --fake-initial

# Recréer la base de données
dropdb kimi_escrow
createdb kimi_escrow
python manage.py migrate
```

### Problèmes de performance

#### Optimisation des requêtes
```python
# Utiliser select_related et prefetch_related
transactions = EscrowTransaction.objects.select_related(
    'buyer', 'seller'
).prefetch_related('milestones', 'proofs')
```

#### Cache Redis
```python
# Configuration du cache dans settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6381/1',
    }
}
```

## 📈 Mise en production

### Checklist de déploiement

- [ ] Variables d'environnement configurées
- [ ] Base de données sauvegardée
- [ ] SSL configuré
- [ ] Logs configurés
- [ ] Monitoring en place
- [ ] Tests passés
- [ ] Documentation mise à jour

### Commandes de déploiement

```bash
# Mise à jour du code
git pull origin main

# Mise à jour des dépendances
pip install -r requirements.txt

# Migrations
python manage.py migrate

# Collecte des fichiers statiques
python manage.py collectstatic --noinput

# Redémarrage des services
sudo systemctl restart gunicorn
sudo systemctl restart celery
sudo systemctl restart nginx
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📞 Support

Pour le support technique :
- Email : support@kimi-escrow.com
- Téléphone : +237 6XX XXX XXX

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [Django](https://www.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery](https://docs.celeryproject.org/)
- [Smile ID](https://usesmileid.com/)
- [MTN Mobile Money](https://momodeveloper.mtn.com/)

---

**Note**: Ce backend est conçu spécifiquement pour le marché camerounais avec intégration des services locaux de paiement mobile et de vérification d'identité.