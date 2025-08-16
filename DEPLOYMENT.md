# Guide de Déploiement Production - KIMI Escrow

## Table des matières

1. [Prérequis](#prérequis)
2. [Installation sur VPS](#installation-sur-vps)
3. [Configuration de la base de données](#configuration-de-la-base-de-données)
4. [Configuration SSL/HTTPS](#configuration-sslhttps)
5. [Configuration des services](#configuration-des-services)
6. [Déploiement initial](#déploiement-initial)
7. [Mise à jour et maintenance](#mise-à-jour-et-maintenance)
8. [Monitoring et logs](#monitoring-et-logs)
9. [Sauvegarde et restauration](#sauvegarde-et-restauration)
10. [Sécurité](#sécurité)
11. [Optimisation des performances](#optimisation-des-performances)
12. [Dépannage](#dépannage)

## Prérequis

### Matériel recommandé
- **CPU**: 2+ cœurs
- **RAM**: 4GB minimum, 8GB recommandé
- **Stockage**: 50GB minimum (SSD recommandé)
- **Bande passante**: 100Mbps minimum

### Système d'exploitation
- Ubuntu 20.04 LTS ou plus récent
- Debian 11 ou plus récent
- CentOS 8+ ou Rocky Linux 8+

### Logiciels requis
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Nginx 1.18+
- Certbot (Let's Encrypt)

## Installation sur VPS

### 1. Mise à jour du système

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

### 2. Installation des dépendances système

```bash
# Paquets de base
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y redis-server nginx
sudo apt install -y certbot python3-certbot-nginx

# Sécurité
sudo apt install -y ufw fail2ban
sudo apt install -y logrotate
```

### 3. Configuration du pare-feu

```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable
```

### 4. Configuration de fail2ban

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Configuration de la base de données

### 1. Configuration PostgreSQL

```bash
# Création de l'utilisateur et de la base
sudo -u postgres createuser --interactive --pwprompt kimi_escrow_user
sudo -u postgres createdb -O kimi_escrow_user kimi_escrow_prod

# Configuration de l'authentification
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Ajouter/modifier dans `pg_hba.conf`:
```
# IPv4 local connections:
host    kimi_escrow_prod    kimi_escrow_user    127.0.0.1/32            md5
```

### 2. Configuration Redis

```bash
sudo nano /etc/redis/redis.conf
```

Modifications recommandées:
```conf
# Sécurité
bind 127.0.0.1
protected-mode yes

# Performance
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistance
save 900 1
save 300 10
save 60 10000
```

## Configuration SSL/HTTPS

### 1. Obtention du certificat Let's Encrypt

   ```bash
# Arrêt temporaire de Nginx
sudo systemctl stop nginx

# Obtention du certificat
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Redémarrage de Nginx
sudo systemctl start nginx
```

### 2. Configuration du renouvellement automatique

   ```bash
# Test du renouvellement
sudo certbot renew --dry-run

# Ajout au cron
sudo crontab -e
```

Ajouter cette ligne:
```
0 12 * * * /usr/bin/certbot renew --quiet
```

## Configuration des services

### 1. Configuration Nginx

   ```bash
# Copie de la configuration
sudo cp nginx.conf /etc/nginx/sites-available/kimi-escrow

# Activation du site
sudo ln -sf /etc/nginx/sites-available/kimi-escrow /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test de la configuration
sudo nginx -t

# Redémarrage
sudo systemctl restart nginx
```

### 2. Configuration systemd

```bash
# Copie des fichiers de service
sudo cp kimi_escrow.service /etc/systemd/system/
sudo cp kimi_escrow-celery.service /etc/systemd/system/
sudo cp kimi_escrow-celerybeat.service /etc/systemd/system/

# Rechargement des services
sudo systemctl daemon-reload

# Activation des services
sudo systemctl enable kimi_escrow
sudo systemctl enable kimi_escrow-celery
sudo systemctl enable kimi_escrow-celerybeat
```

## Déploiement initial

### 1. Clonage du projet

   ```bash
# Création de l'utilisateur
sudo useradd -m -s /bin/bash kimi_escrow
sudo usermod -aG sudo kimi_escrow

# Clonage du projet
sudo mkdir -p /var/www/kimi-escrow
sudo chown kimi_escrow:kimi_escrow /var/www/kimi_escrow
sudo -u kimi_escrow git clone your-git-repo /var/www/kimi-escrow
```

### 2. Configuration de l'environnement

   ```bash
# Copie du fichier d'environnement
sudo cp env.production /var/www/kimi-escrow/.env
sudo chown kimi_escrow:kimi_escrow /var/www/kimi-escrow/.env
sudo chmod 600 /var/www/kimi-escrow/.env

# Édition du fichier .env
sudo -u kimi_escrow nano /var/www/kimi-escrow/.env
```

### 3. Installation des dépendances Python

```bash
cd /var/www/kimi-escrow

# Création de l'environnement virtuel
sudo -u kimi_escrow python3 -m venv venv
sudo -u kimi_escrow venv/bin/pip install --upgrade pip
sudo -u kimi_escrow venv/bin/pip install -r requirements.txt
```

### 4. Configuration de la base de données

```bash
# Migration
sudo -u kimi_escrow venv/bin/python manage.py migrate

# Collecte des fichiers statiques
sudo -u kimi_escrow venv/bin/python manage.py collectstatic --noinput

# Création du superutilisateur
sudo -u kimi_escrow venv/bin/python manage.py createsuperuser
```

### 5. Démarrage des services

```bash
# Démarrage des services
sudo systemctl start kimi_escrow
sudo systemctl start kimi_escrow-celery
sudo systemctl start kimi_escrow-celerybeat

# Vérification du statut
sudo systemctl status kimi_escrow
sudo systemctl status kimi_escrow-celery
sudo systemctl status kimi_escrow-celerybeat
```

## Mise à jour et maintenance

### 1. Script de déploiement

```bash
# Rendre le script exécutable
chmod +x deploy_production.sh

# Mise à jour
./deploy_production.sh update

# Redémarrage
./deploy_production.sh restart

# Vérification du statut
./deploy_production.sh status
```

### 2. Mise à jour manuelle

```bash
cd /var/www/kimi-escrow

# Sauvegarde
sudo -u kimi_escrow venv/bin/python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json

# Pull des modifications
sudo -u kimi_escrow git pull origin main

# Mise à jour des dépendances
sudo -u kimi_escrow venv/bin/pip install -r requirements.txt

# Migration
sudo -u kimi_escrow venv/bin/python manage.py migrate

# Collecte des fichiers statiques
sudo -u kimi_escrow venv/bin/python manage.py collectstatic --noinput

# Redémarrage
sudo systemctl restart kimi_escrow
```

## Monitoring et logs

### 1. Configuration des logs

```bash
# Création des dossiers de logs
sudo mkdir -p /var/www/kimi-escrow/logs
sudo chown kimi_escrow:kimi_escrow /var/www/kimi-escrow/logs

# Rotation des logs
sudo nano /etc/logrotate.d/kimi-escrow
```

Contenu de `/etc/logrotate.d/kimi-escrow`:
```
/var/www/kimi-escrow/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 kimi_escrow kimi_escrow
    postrotate
        systemctl reload kimi_escrow
    endscript
}
```

### 2. Monitoring des services

```bash
# Vérification des logs
sudo journalctl -u kimi_escrow -f
sudo journalctl -u kimi_escrow-celery -f
sudo journalctl -u kimi_escrow-celerybeat -f

# Vérification des ressources
htop
df -h
free -h
```

### 3. Health checks

```bash
# Vérification de l'API
curl -f http://localhost:8000/health/

# Vérification de Nginx
curl -f http://localhost/health/

# Vérification de la base de données
sudo -u postgres psql -d kimi_escrow_prod -c "SELECT 1;"
```

## Sauvegarde et restauration

### 1. Sauvegarde automatique

```bash
# Ajout au cron
sudo crontab -e
```

Ajouter ces lignes:
```
# Sauvegarde quotidienne de la base de données
0 2 * * * /var/www/kimi-escrow/venv/bin/python /var/www/kimi-escrow/manage.py dumpdata > /var/www/kimi-escrow/backups/db_backup_$(date +\%Y\%m\%d).json

# Sauvegarde des fichiers media
0 3 * * * tar -czf /var/www/kimi-escrow/backups/media_backup_$(date +\%Y\%m\%d).tar.gz -C /var/www/kimi-escrow media/

# Nettoyage des anciennes sauvegardes (30 jours)
0 4 * * * find /var/www/kimi-escrow/backups/ -name "*.json" -mtime +30 -delete
0 4 * * * find /var/www/kimi-escrow/backups/ -name "*.tar.gz" -mtime +30 -delete
```

### 2. Restauration

```bash
# Restauration de la base de données
sudo -u kimi_escrow venv/bin/python manage.py loaddata backup_file.json

# Restauration des fichiers media
sudo -u kimi_escrow tar -xzf media_backup_file.tar.gz -C /var/www/kimi-escrow/
```

## Sécurité

### 1. Configuration du pare-feu

```bash
# Vérification des règles
sudo ufw status

# Ajout de règles spécifiques si nécessaire
sudo ufw allow from trusted_ip to any port 22
```

### 2. Configuration fail2ban

```bash
# Vérification des prisons
sudo fail2ban-client status

# Configuration des prisons
sudo nano /etc/fail2ban/jail.local
```

### 3. Mise à jour automatique

```bash
# Installation de unattended-upgrades
sudo apt install -y unattended-upgrades

# Configuration
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Optimisation des performances

### 1. Configuration Nginx

```bash
# Optimisation des workers
sudo nano /etc/nginx/nginx.conf
```

Modifications recommandées:
```nginx
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
gzip on;
gzip_comp_level 6;
```

### 2. Configuration PostgreSQL

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Modifications recommandées:
```conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### 3. Configuration Redis

```bash
sudo nano /etc/redis/redis.conf
```

Modifications recommandées:
```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Dépannage

### 1. Problèmes courants

#### Service ne démarre pas
```bash
# Vérification des logs
sudo journalctl -u kimi_escrow -n 50

# Vérification de la configuration
sudo -u kimi_escrow venv/bin/python manage.py check

# Vérification des permissions
ls -la /var/www/kimi-escrow/
```

#### Problèmes de base de données
```bash
# Vérification de la connexion
sudo -u postgres psql -d kimi_escrow_prod -c "SELECT version();"

# Vérification des migrations
sudo -u kimi_escrow venv/bin/python manage.py showmigrations
```

#### Problèmes de Celery
```bash
# Vérification du statut
sudo systemctl status kimi_escrow-celery

# Vérification des logs
sudo journalctl -u kimi_escrow-celery -f

# Test de connexion Redis
redis-cli ping
```

### 2. Commandes utiles

```bash
# Redémarrage complet
sudo systemctl restart kimi_escrow kimi_escrow-celery kimi_escrow-celerybeat nginx

# Vérification des ports
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :6379

# Vérification des processus
ps aux | grep python
ps aux | grep celery

# Nettoyage du cache Redis
redis-cli flushall
```

### 3. Support et maintenance

- **Logs d'erreur**: `/var/www/kimi-escrow/logs/`
- **Logs système**: `/var/log/`
- **Configuration**: `/etc/nginx/sites-available/kimi-escrow`
- **Services**: `systemctl status kimi_escrow*`

## Conclusion

Ce guide couvre l'ensemble du processus de déploiement et de maintenance de KIMI Escrow en production. Pour toute question ou problème spécifique, consultez les logs et utilisez les commandes de diagnostic fournies.

**Rappel important**: N'oubliez jamais de :
- Sauvegarder régulièrement vos données
- Maintenir vos certificats SSL à jour
- Surveiller les performances et la sécurité
- Tester vos sauvegardes
- Documenter toute modification de configuration
