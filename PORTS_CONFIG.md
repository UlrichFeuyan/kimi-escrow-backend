# Configuration des Ports - Kimi Escrow Backend

## 🔌 Nouvelle Configuration des Ports

### **Ports Externes (Accessibles depuis l'extérieur)**
- **Port 8003** → Application Django (interne: 8000)
- **Port 5437** → PostgreSQL (interne: 5432)
- **Port 6382** → Redis (interne: 6379)
- **Port 8080** → Nginx HTTP (interne: 80)
- **Port 8443** → Nginx HTTPS (interne: 443)

### **Ports Internes (Docker)**
- **Port 8000** → Application Django
- **Port 5432** → PostgreSQL
- **Port 6379** → Redis
- **Port 80** → Nginx HTTP
- **Port 443** → Nginx HTTPS

## 📱 URLs d'Accès

### **Application**
- **Application web** : http://localhost:8003
- **Admin Django** : http://localhost:8003/admin/
- **API Swagger** : http://localhost:8003/swagger/

### **Services de Base**
- **Base de données** : localhost:5437
- **Redis** : localhost:6382

### **Proxy Nginx**
- **HTTP** : http://localhost:8080
- **HTTPS** : https://localhost:8443

## 🔧 Configuration Docker Compose

### **docker-compose.yml**
```yaml
services:
  db:
    ports:
      - "5437:5432"  # Externe:Interne
  
  redis:
    ports:
      - "6382:6379"  # Externe:Interne
  
  web:
    ports:
      - "8003:8000"  # Externe:Interne
  
  nginx:
    ports:
      - "8080:80"    # Externe:Interne
      - "8443:443"   # Externe:Interne
```

### **docker-compose.prod.yml**
```yaml
services:
  db:
    ports:
      - "5437:5432"
  
  redis:
    ports:
      - "6382:6379"
  
  web:
    ports:
      - "8003:8000"
  
  nginx:
    ports:
      - "8080:80"
      - "8443:443"
```

## 🌐 Configuration des Variables d'Environnement

### **Fichier .env**
```bash
# Base de données
DB_HOST=db
DB_PORT=5432  # Port interne Docker

# Redis
REDIS_URL=redis://redis:6379/0  # Port interne Docker
```

## 🔍 Vérification des Ports

### **Script de vérification**
```bash
./check_status.sh
```

### **Vérification manuelle**
```bash
# Vérifier les ports ouverts
sudo netstat -tulpn | grep -E ':(8003|5437|6382|8080|8443)'

# Tester l'application
curl http://localhost:8003/api/core/health/

# Tester la base de données
docker-compose exec db pg_isready -U postgres

# Tester Redis
docker-compose exec redis redis-cli ping
```

## 🚨 Résolution des Conflits

### **Ports à Libérer**
- **Port 80** : Arrêter Nginx local
- **Port 443** : Arrêter Nginx local
- **Port 5432** : Arrêter PostgreSQL local
- **Port 6379** : Arrêter Redis local
- **Port 8000** : Arrêter les applications Python locales

### **Commandes de libération**
```bash
# Arrêter les services locaux
sudo systemctl stop nginx
sudo systemctl stop postgresql
sudo systemctl stop redis-server

# Désactiver au démarrage
sudo systemctl disable nginx
sudo systemctl disable postgresql
sudo systemctl disable redis-server
```

## 📋 Migration depuis l'Ancienne Configuration

### **Changements Effectués**
1. ✅ Port 8000 → 8003 (Application)
2. ✅ Port 5434 → 5437 (PostgreSQL)
3. ✅ Port 6381 → 6382 (Redis)
4. ✅ Port 80 → 8080 (Nginx HTTP)
5. ✅ Port 443 → 8443 (Nginx HTTPS)

### **URLs Mises à Jour**
- **Ancien** : http://localhost:8000 → **Nouveau** : http://localhost:8003
- **Ancien** : localhost:5434 → **Nouveau** : localhost:5437
- **Ancien** : localhost:6381 → **Nouveau** : localhost:6382

## 🔒 Sécurité

### **Avantages de la Nouvelle Configuration**
- **Évite les conflits** avec les services système
- **Ports non-standard** réduisent les attaques automatisées
- **Séparation claire** entre ports internes et externes
- **Facilite le déploiement** sur serveurs avec services existants

### **Recommandations**
- **Changer les mots de passe** par défaut
- **Configurer un pare-feu** pour restreindre l'accès
- **Utiliser HTTPS** en production (port 8443)
- **Surveiller les logs** d'accès

---

**Note** : Cette configuration évite les conflits avec les services Ubuntu standard et facilite le déploiement sur serveurs de développement.
