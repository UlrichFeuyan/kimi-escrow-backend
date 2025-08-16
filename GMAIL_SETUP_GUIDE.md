# Guide de Configuration Gmail pour Django - Kimi Escrow

## 🎯 Objectif
Configurer Gmail pour envoyer des emails depuis Django, notamment pour la réinitialisation de mot de passe.

## ⚠️ Important
**NE JAMAIS utiliser votre mot de passe normal de compte Google !**
Utilisez toujours un "App Password" de 16 caractères.

## 🔧 Étapes de Configuration

### 1. Activer l'Authentification à 2 Facteurs

1. **Allez sur [myaccount.google.com](https://myaccount.google.com)**
2. **Sécurité** → **Connexion à Google** → **Authentification à 2 facteurs**
3. **Activez-la** si ce n'est pas déjà fait
4. **Choisissez une méthode** (SMS, app Google Authenticator, etc.)

### 2. Créer un App Password

1. **Sécurité** → **Connexion à Google** → **Mots de passe des applications**
2. **Sélectionnez "Mail"** dans le menu déroulant
3. **Choisissez votre appareil** (Windows, Mac, Linux, etc.)
4. **Cliquez sur "Générer"**
5. **Copiez le mot de passe de 16 caractères** (ex: `abcd efgh ijkl mnop`)

### 3. Configuration Django

#### Option A : Variables d'environnement (.env)
```bash
# Configuration Email Gmail
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-app-password-16-caracteres
DEFAULT_FROM_EMAIL=votre-email@gmail.com
SERVER_EMAIL=votre-email@gmail.com
```

#### Option B : Fichier de configuration (settings_gmail.py)
```python
# kimi_escrow/settings_gmail.py
from .settings import *

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'votre-email@gmail.com'
EMAIL_HOST_PASSWORD = 'votre-app-password-16-caracteres'
DEFAULT_FROM_EMAIL = 'votre-email@gmail.com'
SERVER_EMAIL = 'votre-email@gmail.com'
```

### 4. Utilisation

#### Démarrage avec configuration Gmail
```bash
# Option 1 : Variables d'environnement
export EMAIL_HOST_PASSWORD="votre-app-password"
python manage.py runserver

# Option 2 : Fichier de configuration
DJANGO_SETTINGS_MODULE=kimi_escrow.settings_gmail python manage.py runserver
```

#### Test de la configuration
```bash
python test_email.py
```

## 🧪 Test de la Configuration

### 1. Test basique
```bash
python test_email.py
```

### 2. Test de l'API de réinitialisation
```bash
# Démarrer le serveur
DJANGO_SETTINGS_MODULE=kimi_escrow.settings_gmail python manage.py runserver 0.0.0.0:8001

# Tester l'API
curl -X POST http://localhost:8001/api/auth/password-reset/request/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}'
```

## 🔍 Dépannage

### Erreur : "Username and Password not accepted"

**Causes possibles :**
1. **App Password incorrect** : Vérifiez que vous utilisez un App Password de 16 caractères
2. **Authentification à 2 facteurs non activée** : Activez-la d'abord
3. **App Password expiré** : Générez un nouveau App Password
4. **Compte Google bloqué** : Vérifiez l'état de votre compte

**Solutions :**
1. **Regénérez un App Password** :
   - Sécurité → Connexion à Google → Mots de passe des applications
   - Supprimez l'ancien et créez-en un nouveau
2. **Vérifiez l'authentification à 2 facteurs** : Elle doit être active
3. **Testez avec le script** : `python test_email.py`

### Erreur : "Connection refused"

**Causes possibles :**
1. **Port bloqué** : Le port 587 peut être bloqué par votre pare-feu
2. **Gmail temporairement indisponible**

**Solutions :**
1. **Vérifiez votre pare-feu** : Autorisez le port 587
2. **Testez plus tard** : Gmail peut avoir des problèmes temporaires
3. **Utilisez le port 465 avec SSL** (alternative) :
   ```python
   EMAIL_PORT = 465
   EMAIL_USE_SSL = True
   EMAIL_USE_TLS = False
   ```

## 📱 Configuration Alternative

### Pour le Développement
Utilisez le backend console pour voir les emails dans la console :
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Pour la Production
Utilisez un service SMTP professionnel :
- **SendGrid**
- **Mailgun**
- **Amazon SES**
- **Postmark**

## 🔒 Sécurité

### Bonnes Pratiques
1. **Ne commitez jamais** vos App Passwords dans le code
2. **Utilisez des variables d'environnement** ou des fichiers de configuration séparés
3. **Limitez l'accès** aux App Passwords
4. **Régénérez régulièrement** vos App Passwords

### Variables d'environnement recommandées
```bash
# .env (ne pas commiter)
EMAIL_HOST_PASSWORD=votre-app-password-secret

# .env.example (à commiter)
EMAIL_HOST_PASSWORD=your-app-password-here
```

## ✅ Vérification

### Checklist de Configuration
- [ ] Authentification à 2 facteurs activée
- [ ] App Password de 16 caractères généré
- [ ] Configuration Django mise à jour
- [ ] Test d'envoi d'email réussi
- [ ] API de réinitialisation fonctionnelle
- [ ] Variables d'environnement sécurisées

## 🚀 Prochaines Étapes

1. **Testez en production** avec un vrai compte utilisateur
2. **Configurez la limitation de taux** pour éviter le spam
3. **Implémentez la journalisation** des tentatives d'envoi
4. **Ajoutez des templates d'email** personnalisés
5. **Configurez la gestion des erreurs** d'envoi

## 📞 Support

Si vous rencontrez des problèmes :
1. **Vérifiez ce guide** étape par étape
2. **Testez avec le script** `test_email.py`
3. **Consultez les logs Django** pour les erreurs détaillées
4. **Vérifiez la configuration Gmail** sur votre compte Google
