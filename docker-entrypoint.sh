#!/bin/bash

# Fonction pour attendre qu'un service soit disponible
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "En attente de $service_name sur $host:$port..."
    while ! nc -z $host $port; do
        sleep 1
    done
    echo "$service_name est disponible!"
}

# Attendre PostgreSQL
wait_for_service $DB_HOST $DB_PORT "PostgreSQL"

# Attendre Redis
wait_for_service ${REDIS_URL#redis://} ${REDIS_URL##*:} "Redis" 2>/dev/null || echo "Redis check skipped"

# Appliquer les migrations
echo "Application des migrations..."
python manage.py migrate

# Créer un superutilisateur si défini
if [ "$DJANGO_SUPERUSER_PHONE" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Création du superutilisateur..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(phone_number='$DJANGO_SUPERUSER_PHONE').exists():
    User.objects.create_superuser(
        phone_number='$DJANGO_SUPERUSER_PHONE',
        password='$DJANGO_SUPERUSER_PASSWORD',
        first_name='Admin',
        last_name='System'
    )
    print('Superutilisateur créé avec succès')
else:
    print('Superutilisateur existe déjà')
"
fi

# Collecter les fichiers statiques
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Créer les répertoires de logs s'ils n'existent pas
mkdir -p logs

# Initialiser les paramètres par défaut
echo "Initialisation des paramètres par défaut..."
python manage.py shell -c "
from core.models import GlobalSettings

# Paramètres par défaut
defaults = [
    ('ESCROW_COMMISSION_RATE', '0.025', 'Taux de commission (2.5%)'),
    ('MINIMUM_ESCROW_AMOUNT', '1000', 'Montant minimum pour une transaction (XAF)'),
    ('MAXIMUM_ESCROW_AMOUNT', '10000000', 'Montant maximum pour une transaction (XAF)'),
    ('DISPUTE_TIMEOUT_DAYS', '7', 'Délai pour créer un litige (jours)'),
    ('AUTO_RELEASE_DAYS', '14', 'Délai de libération automatique (jours)'),
    ('KYC_REQUIRED', 'True', 'KYC requis pour les transactions'),
    ('MAINTENANCE_MODE', 'False', 'Mode maintenance'),
]

for key, value, description in defaults:
    setting, created = GlobalSettings.objects.get_or_create(
        key=key,
        defaults={'value': value, 'description': description}
    )
    if created:
        print(f'Paramètre créé: {key} = {value}')
    else:
        print(f'Paramètre existe: {key} = {setting.value}')
"

echo "Initialisation terminée!"

# Démarrer l'application
if [ "$1" = "runserver" ]; then
    echo "Démarrage du serveur de développement..."
    exec python manage.py runserver 0.0.0.0:8000
elif [ "$1" = "celery" ]; then
    echo "Démarrage de Celery worker..."
    exec celery -A kimi_escrow worker --loglevel=info
elif [ "$1" = "celery-beat" ]; then
    echo "Démarrage de Celery beat..."
    exec celery -A kimi_escrow beat --loglevel=info
else
    echo "Démarrage de Gunicorn..."
    exec gunicorn kimi_escrow.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 50
fi
