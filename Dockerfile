FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gettext \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copier le projet
COPY . /app/

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs
RUN mkdir -p /app/media
RUN mkdir -p /app/staticfiles

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput --settings=kimi_escrow.settings

# Exposer le port
EXPOSE 8000

# Script de démarrage
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Commande par défaut
CMD ["/app/docker-entrypoint.sh"]
