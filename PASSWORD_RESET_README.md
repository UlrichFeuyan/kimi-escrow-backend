# Réinitialisation de Mot de Passe - Kimi Escrow

## Vue d'ensemble

La fonctionnalité de réinitialisation de mot de passe permet aux utilisateurs de récupérer l'accès à leur compte en cas d'oubli de mot de passe. Le processus se fait entièrement par email pour plus de sécurité.

## Architecture

### Backend API

#### Endpoints

1. **Demande de réinitialisation**
   - **URL**: `POST /api/auth/password-reset/request/`
   - **Description**: Envoie un email avec un code de réinitialisation
   - **Corps de la requête**:
     ```json
     {
       "email": "user@example.com"
     }
     ```
   - **Réponse**:
     ```json
     {
       "success": true,
       "message": "Un email de réinitialisation a été envoyé à votre adresse email.",
       "data": {
         "email": "user@example.com",
         "expires_in_minutes": 15
       }
     }
     ```

2. **Confirmation de réinitialisation**
   - **URL**: `POST /api/auth/password-reset/confirm/`
   - **Description**: Confirme la réinitialisation avec le code reçu
   - **Corps de la requête**:
     ```json
     {
       "email": "user@example.com",
       "reset_code": "123456",
       "new_password": "NewPassword123!"
     }
     ```
   - **Réponse**:
     ```json
     {
       "success": true,
       "message": "Votre mot de passe a été réinitialisé avec succès.",
       "data": {
         "email": "user@example.com",
         "password_changed_at": "2025-08-12T07:30:00Z"
       }
     }
     ```

#### Modèles

- **CustomUser**: Ajout des champs :
  - `password_reset_token`: Code de réinitialisation (6 chiffres)
  - `password_reset_expires_at`: Date d'expiration du token

#### Méthodes du modèle

- `generate_password_reset_token()`: Génère un nouveau token valide 15 minutes
- `verify_password_reset_token(token)`: Vérifie la validité d'un token

#### Tâches Celery

- `send_password_reset_email(user_id, reset_code)`: Envoie l'email de réinitialisation

### Frontend

#### Templates

1. **password_reset.html**: Formulaire de demande de réinitialisation
2. **password_reset_confirm.html**: Formulaire de confirmation avec nouveau mot de passe

#### Formulaires

1. **PasswordResetForm**: Demande de réinitialisation par email
2. **SetPasswordForm**: Confirmation avec code et nouveau mot de passe

## Flux d'utilisation

### 1. Demande de réinitialisation

1. L'utilisateur accède à la page "Mot de passe oublié"
2. Il saisit son adresse email
3. Le système vérifie que l'email existe
4. Un code de réinitialisation est généré et envoyé par email
5. Le code expire après 15 minutes

### 2. Confirmation de réinitialisation

1. L'utilisateur reçoit l'email avec le code
2. Il saisit le code et son nouveau mot de passe
3. Le système vérifie le code et valide le nouveau mot de passe
4. Le mot de passe est mis à jour
5. Le token de réinitialisation est invalidé

## Sécurité

### Mesures de sécurité

- **Expiration automatique**: Les tokens expirent après 15 minutes
- **Validation stricte**: Vérification de l'existence de l'email
- **Validation du mot de passe**: Respect des règles de complexité Django
- **Invalidation après utilisation**: Le token est supprimé après utilisation

### Validation des mots de passe

Le nouveau mot de passe doit respecter :
- Minimum 8 caractères
- Au moins une majuscule
- Au moins une minuscule
- Au moins un chiffre
- Pas de similarité avec les informations personnelles

## Configuration

### Variables d'environnement

```bash
# Configuration email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@kimi-escrow.com
```

### Tâches Celery

Assurez-vous que Celery est configuré et en cours d'exécution :

```bash
# Démarrer Celery
celery -A kimi_escrow worker -l info

# Démarrer Celery Beat (si nécessaire)
celery -A kimi_escrow beat -l info
```

## Tests

### Test manuel

1. Démarrer le serveur Django :
   ```bash
   python manage.py runserver
   ```

2. Utiliser le script de test :
   ```bash
   python test_password_reset.py
   ```

### Test via Swagger

1. Accéder à la documentation Swagger : `http://localhost:8000/swagger/`
2. Tester les endpoints de réinitialisation de mot de passe

## Dépannage

### Problèmes courants

1. **Email non envoyé**
   - Vérifier la configuration SMTP
   - Vérifier que Celery est en cours d'exécution
   - Consulter les logs Celery

2. **Token expiré**
   - Le token expire après 15 minutes
   - Demander un nouveau token

3. **Email non trouvé**
   - Vérifier que l'email existe dans la base de données
   - Vérifier la casse de l'email

### Logs

Les logs sont disponibles dans :
- **Django**: `python manage.py runserver --verbosity 2`
- **Celery**: `celery -A kimi_escrow worker -l debug`

## Évolutions futures

### Améliorations possibles

1. **Limitation de taux**: Limiter le nombre de demandes par email
2. **Audit trail**: Enregistrer toutes les tentatives de réinitialisation
3. **Notifications**: Envoyer une confirmation de changement de mot de passe
4. **Sécurité renforcée**: Ajouter des questions de sécurité
5. **Support multi-langue**: Traduire les emails selon la langue de l'utilisateur

## Support

Pour toute question ou problème :
- Consulter la documentation Swagger
- Vérifier les logs d'erreur
- Contacter l'équipe de développement
