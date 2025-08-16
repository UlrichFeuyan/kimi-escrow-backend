#!/bin/bash

# Script de déploiement production pour KIMI Escrow
# Usage: ./deploy_production.sh [install|update|restart|ssl]

set -e

# Configuration
PROJECT_NAME="kimi-escrow"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"
GIT_REPO="your-git-repo-url"
DOMAIN="yourdomain.com"
EMAIL="admin@yourdomain.com"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERREUR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[ATTENTION] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    if [[ $EUID -eq 0 ]]; then
        error "Ce script ne doit pas être exécuté en tant que root"
    fi
    
    if ! command -v git &> /dev/null; then
        error "Git n'est pas installé"
    fi
    
    if ! command -v python3 &> /dev/null; then
        error "Python 3 n'est pas installé"
    fi
    
    if ! command -v pip3 &> /dev/null; then
        error "pip3 n'est pas installé"
    fi
    
    log "Prérequis vérifiés ✓"
}

# Installation initiale
install() {
    log "Installation initiale de KIMI Escrow..."
    
    # Mise à jour du système
    log "Mise à jour du système..."
    sudo apt update && sudo apt upgrade -y
    
    # Installation des paquets nécessaires
    log "Installation des paquets système..."
    sudo apt install -y python3-pip python3-venv python3-dev \
                       postgresql postgresql-contrib \
                       redis-server nginx \
                       certbot python3-certbot-nginx \
                       ufw fail2ban \
                       curl wget unzip
    
    # Configuration de PostgreSQL
    log "Configuration de PostgreSQL..."
    sudo -u postgres createuser --interactive --pwprompt kimi_escrow_user
    sudo -u postgres createdb -O kimi_escrow_user kimi_escrow_prod
    
    # Configuration de Redis
    log "Configuration de Redis..."
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    
    # Configuration du pare-feu
    log "Configuration du pare-feu..."
    sudo ufw allow ssh
    sudo ufw allow 80
    sudo ufw allow 443
    sudo ufw --force enable
    
    # Configuration de fail2ban
    log "Configuration de fail2ban..."
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    # Création de l'utilisateur système
    log "Création de l'utilisateur système..."
    sudo useradd -m -s /bin/bash kimi_escrow
    sudo usermod -aG sudo kimi_escrow
    
    # Clonage du projet
    log "Clonage du projet..."
    sudo mkdir -p $PROJECT_DIR
    sudo chown kimi_escrow:kimi_escrow $PROJECT_DIR
    sudo -u kimi_escrow git clone $GIT_REPO $PROJECT_DIR
    
    # Configuration de l'environnement virtuel
    log "Configuration de l'environnement virtuel..."
    sudo -u kimi_escrow python3 -m venv $VENV_DIR
    sudo -u kimi_escrow $VENV_DIR/bin/pip install --upgrade pip
    sudo -u kimi_escrow $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    
    # Configuration des variables d'environnement
    log "Configuration des variables d'environnement..."
    sudo cp $PROJECT_DIR/env.production $PROJECT_DIR/.env
    sudo chown kimi_escrow:kimi_escrow $PROJECT_DIR/.env
    sudo chmod 600 $PROJECT_DIR/.env
    
    # Configuration de Nginx
    log "Configuration de Nginx..."
    sudo tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    client_max_body_size 25M;
    
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
EOF
    
    sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Configuration de systemd
    log "Configuration de systemd..."
    sudo tee /etc/systemd/system/$PROJECT_NAME.service > /dev/null <<EOF
[Unit]
Description=KIMI Escrow Django Application
After=network.target

[Service]
Type=simple
User=kimi_escrow
Group=kimi_escrow
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 kimi_escrow.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    # Configuration de Celery
    sudo tee /etc/systemd/system/$PROJECT_NAME-celery.service > /dev/null <<EOF
[Unit]
Description=KIMI Escrow Celery Worker
After=network.target

[Service]
Type=simple
User=kimi_escrow
Group=kimi_escrow
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/celery -A kimi_escrow worker --loglevel=info
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    # Configuration de Celery Beat
    sudo tee /etc/systemd/system/$PROJECT_NAME-celerybeat.service > /dev/null <<EOF
[Unit]
Description=KIMI Escrow Celery Beat
After=network.target

[Service]
Type=simple
User=kimi_escrow
Group=kimi_escrow
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/celery -A kimi_escrow beat --loglevel=info
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    # Activation des services
    sudo systemctl daemon-reload
    sudo systemctl enable $PROJECT_NAME
    sudo systemctl enable $PROJECT_NAME-celery
    sudo systemctl enable $PROJECT_NAME-celerybeat
    
    # Création des dossiers nécessaires
    sudo -u kimi_escrow mkdir -p $PROJECT_DIR/logs
    sudo -u kimi_escrow mkdir -p $PROJECT_DIR/media
    sudo -u kimi_escrow mkdir -p $PROJECT_DIR/backups
    
    # Configuration des permissions
    sudo chown -R kimi_escrow:kimi_escrow $PROJECT_DIR
    sudo chmod -R 755 $PROJECT_DIR
    
    log "Installation terminée ✓"
    warning "N'oubliez pas de configurer le fichier .env avec vos vraies valeurs !"
}

# Mise à jour du projet
update() {
    log "Mise à jour du projet..."
    
    cd $PROJECT_DIR
    
    # Sauvegarde de la base de données
    log "Sauvegarde de la base de données..."
    sudo -u kimi_escrow $VENV_DIR/bin/python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
    
    # Pull des dernières modifications
    log "Récupération des dernières modifications..."
    sudo -u kimi_escrow git pull origin main
    
    # Mise à jour des dépendances
    log "Mise à jour des dépendances..."
    sudo -u kimi_escrow $VENV_DIR/bin/pip install -r requirements.txt
    
    # Migration de la base de données
    log "Migration de la base de données..."
    sudo -u kimi_escrow $VENV_DIR/bin/python manage.py migrate
    
    # Collecte des fichiers statiques
    log "Collecte des fichiers statiques..."
    sudo -u kimi_escrow $VENV_DIR/bin/python manage.py collectstatic --noinput
    
    # Redémarrage des services
    restart
    
    log "Mise à jour terminée ✓"
}

# Redémarrage des services
restart() {
    log "Redémarrage des services..."
    
    sudo systemctl restart $PROJECT_NAME
    sudo systemctl restart $PROJECT_NAME-celery
    sudo systemctl restart $PROJECT_NAME-celerybeat
    sudo systemctl restart nginx
    
    log "Services redémarrés ✓"
}

# Configuration SSL avec Let's Encrypt
ssl() {
    log "Configuration SSL avec Let's Encrypt..."
    
    # Arrêt temporaire de Nginx
    sudo systemctl stop nginx
    
    # Obtention du certificat SSL
    sudo certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive
    
    # Redémarrage de Nginx
    sudo systemctl start nginx
    
    # Test de la configuration SSL
    sudo nginx -t
    
    # Configuration du renouvellement automatique
    sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -
    
    log "SSL configuré ✓"
}

# Vérification du statut
status() {
    log "Statut des services..."
    
    echo "=== Django ==="
    sudo systemctl status $PROJECT_NAME --no-pager -l
    
    echo -e "\n=== Celery Worker ==="
    sudo systemctl status $PROJECT_NAME-celery --no-pager -l
    
    echo -e "\n=== Celery Beat ==="
    sudo systemctl status $PROJECT_NAME-celerybeat --no-pager -l
    
    echo -e "\n=== Nginx ==="
    sudo systemctl status nginx --no-pager -l
    
    echo -e "\n=== PostgreSQL ==="
    sudo systemctl status postgresql --no-pager -l
    
    echo -e "\n=== Redis ==="
    sudo systemctl status redis-server --no-pager -l
}

# Sauvegarde
backup() {
    log "Sauvegarde du projet..."
    
    BACKUP_DIR="$PROJECT_DIR/backups"
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
    
    # Création du dossier de sauvegarde
    sudo -u kimi_escrow mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    # Sauvegarde de la base de données
    log "Sauvegarde de la base de données..."
    sudo -u kimi_escrow $VENV_DIR/bin/python manage.py dumpdata > "$BACKUP_DIR/$BACKUP_NAME/database.json"
    
    # Sauvegarde des fichiers media
    log "Sauvegarde des fichiers media..."
    sudo -u kimi_escrow tar -czf "$BACKUP_DIR/$BACKUP_NAME/media.tar.gz" -C $PROJECT_DIR media/
    
    # Sauvegarde des logs
    log "Sauvegarde des logs..."
    sudo -u kimi_escrow tar -czf "$BACKUP_DIR/$BACKUP_NAME/logs.tar.gz" -C $PROJECT_DIR logs/
    
    # Création de l'archive de sauvegarde
    cd "$BACKUP_DIR"
    sudo -u kimi_escrow tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME/"
    sudo -u kimi_escrow rm -rf "$BACKUP_NAME"
    
    log "Sauvegarde créée: $BACKUP_DIR/${BACKUP_NAME}.tar.gz ✓"
}

# Nettoyage des anciennes sauvegardes
cleanup() {
    log "Nettoyage des anciennes sauvegardes..."
    
    BACKUP_DIR="$PROJECT_DIR/backups"
    RETENTION_DAYS=30
    
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    log "Nettoyage terminé ✓"
}

# Aide
usage() {
    echo "Usage: $0 [install|update|restart|ssl|status|backup|cleanup]"
echo ""
    echo "Commandes:"
    echo "  install   - Installation initiale complète"
    echo "  update    - Mise à jour du projet"
    echo "  restart   - Redémarrage des services"
    echo "  ssl       - Configuration SSL avec Let's Encrypt"
    echo "  status    - Vérification du statut des services"
    echo "  backup    - Création d'une sauvegarde"
    echo "  cleanup   - Nettoyage des anciennes sauvegardes"
echo ""
    echo "Exemples:"
    echo "  $0 install    # Installation initiale"
    echo "  $0 update     # Mise à jour"
    echo "  $0 ssl        # Configuration SSL"
}

# Script principal
main() {
    case "${1:-}" in
        install)
            check_prerequisites
            install
            ;;
        update)
            update
            ;;
        restart)
            restart
            ;;
        ssl)
            ssl
            ;;
        status)
            status
            ;;
        backup)
            backup
            ;;
        cleanup)
            cleanup
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# Exécution du script
main "$@"
