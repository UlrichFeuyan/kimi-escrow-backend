# Guide de Test Manuel - Workflow de Réinitialisation de Mot de Passe

## 🎯 Objectif
Tester le workflow complet de réinitialisation de mot de passe avec les nouvelles pages frontend.

## 🚀 Prérequis
- Serveur Django démarré sur `http://localhost:8003`
- Configuration Gmail active (DJANGO_SETTINGS_MODULE=kimi_escrow.settings_gmail)
- Email de test : `djofangulrich05@gmail.com`

## 📋 Étapes de Test

### **ÉTAPE 1 : Demande de Réinitialisation**
1. **Ouvrez votre navigateur** : `http://localhost:8003/password-reset/`
2. **Vérifiez la page** :
   - ✅ Titre : "Réinitialisation de mot de passe - Kimi Escrow"
   - ✅ Formulaire avec champ email
   - ✅ Design professionnel
3. **Saisissez l'email** : `djofangulrich05@gmail.com`
4. **Cliquez sur "Envoyer"**
5. **Attendu** : Redirection vers `/password-reset/code/`

### **ÉTAPE 2 : Validation du Code**
1. **Vérifiez la nouvelle page** :
   - ✅ URL : `http://localhost:8003/password-reset/code/`
   - ✅ Indicateur d'étapes (3 cercles)
   - ✅ Affichage de l'email envoyé
   - ✅ Champ de code à 6 chiffres centré
2. **Consultez votre email Gmail** :
   - ✅ Email avec design HTML professionnel
   - ✅ Code à 6 chiffres dans le bloc vert
   - ✅ Instructions de sécurité
3. **Saisissez le code reçu** (ex: 643085)
4. **Attendu** : Redirection vers `/password-reset/confirm/`

### **ÉTAPE 3 : Nouveau Mot de Passe**
1. **Vérifiez la page finale** :
   - ✅ URL : `http://localhost:8003/password-reset/confirm/`
   - ✅ Indicateur d'étapes (3 cercles, 3ème actif)
   - ✅ Affichage de l'email de réinitialisation
   - ✅ Champs de mot de passe avec validation
2. **Saisissez un nouveau mot de passe** :
   - Exemple : `NewSecurePassword123!`
   - Confirmez le mot de passe
3. **Cliquez sur "Changer le mot de passe"**
4. **Attendu** : Redirection vers `/login/` avec message de succès

### **ÉTAPE 4 : Test de Connexion**
1. **Sur la page de connexion** :
   - Email : `djofangulrich05@gmail.com`
   - Mot de passe : `NewSecurePassword123!`
2. **Cliquez sur "Se connecter"**
3. **Attendu** : Connexion réussie avec redirection vers le dashboard

### **ÉTAPE 5 : Vérification Email**
1. **Consultez votre boîte email**
2. **Attendu** : Réception d'un 2ème email de notification
   - Sujet : "Mot de passe modifié - Kimi Escrow"
   - Contenu : Confirmation du changement avec horodatage

## 🔍 Points de Vérification

### **Design et UX**
- [ ] Indicateurs d'étapes visuels et clairs
- [ ] Messages d'erreur informatifs
- [ ] Design responsive sur mobile
- [ ] Cohérence avec le style Kimi Escrow
- [ ] Boutons et liens fonctionnels

### **Sécurité**
- [ ] Redirection automatique sans session
- [ ] Expiration du code après 15 minutes
- [ ] Validation stricte des mots de passe
- [ ] Nettoyage des sessions après succès

### **Notifications**
- [ ] Email de réinitialisation reçu rapidement
- [ ] Design HTML professionnel
- [ ] Code lisible et copiable
- [ ] Email de confirmation reçu

## 🐛 Résolution de Problèmes

### **Email non reçu**
```bash
# Vérifiez les logs du serveur
tail -f /path/to/logs/django.log

# Vérifiez la configuration SMTP
python test_email.py
```

### **Erreur de redirection**
- Vérifiez que la session est maintenue
- Consultez les logs du navigateur (F12)
- Vérifiez les cookies de session

### **Code invalide**
- Vérifiez l'expiration (15 minutes max)
- Utilisez le debug_token des logs si disponible
- Redémarrez le processus si nécessaire

## 📊 Résultats Attendus

### **Workflow Complet Réussi** ✅
1. **Demande** → Email envoyé + redirection
2. **Code** → Validation + redirection  
3. **Mot de passe** → Changement + redirection
4. **Connexion** → Authentification réussie
5. **Notification** → Email de confirmation reçu

### **Métriques de Performance**
- **Temps d'envoi email** : < 5 secondes
- **Redirection** : Immédiate
- **Validation** : Temps réel
- **UX globale** : Fluide et intuitive

## 🎉 Validation Finale

Une fois tous les tests passés :
- ✅ **Workflow fonctionnel de A à Z**
- ✅ **Design professionnel et moderne**
- ✅ **Sécurité respectée**
- ✅ **Emails HTML magnifiques**
- ✅ **Prêt pour la production**

## 📞 Support

En cas de problème :
1. Consultez les logs Django
2. Vérifiez la configuration Gmail
3. Testez l'API directement avec curl
4. Redémarrez le serveur si nécessaire
