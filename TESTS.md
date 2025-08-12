# 🧪 Tests de l'API Kimi Escrow

Ce document décrit la stratégie de tests complète pour l'API Kimi Escrow, couvrant tous les endpoints et fonctionnalités.

## 📋 Vue d'ensemble

La suite de tests comprend :
- **Tests unitaires** pour chaque module
- **Tests d'intégration** pour les flux complets
- **Tests de permissions** pour la sécurité
- **Tests de performance** pour l'optimisation
- **Analyse de couverture** de code

## 🗂️ Structure des tests

```
tests/
├── users/tests.py              # Tests authentification & KYC
├── escrow/tests.py             # Tests transactions escrow
├── payments/tests.py           # Tests paiements Mobile Money
├── disputes/tests.py           # Tests système de litiges
├── core/tests.py              # Tests fonctionnalités core
├── test_integration.py        # Tests d'intégration E2E
├── run_tests.py              # Script d'exécution complet
└── pytest.ini               # Configuration pytest
```

## 🚀 Exécution des tests

### Méthode 1: Script automatique (Recommandé)
```bash
# Exécuter tous les tests avec rapport complet
python run_tests.py
```

### Méthode 2: Django Test Runner
```bash
# Tous les tests
python manage.py test

# Tests spécifiques par module
python manage.py test users.tests
python manage.py test escrow.tests
python manage.py test payments.tests
python manage.py test disputes.tests
python manage.py test core.tests

# Tests d'intégration
python manage.py test test_integration
```

### Méthode 3: Pytest (Avancé)
```bash
# Installer pytest-django
pip install pytest-django

# Exécuter tous les tests
pytest

# Tests par catégorie
pytest -m auth          # Tests d'authentification
pytest -m escrow        # Tests escrow
pytest -m payments      # Tests paiements
pytest -m disputes      # Tests litiges
pytest -m integration   # Tests d'intégration

# Tests avec couverture
pytest --cov=. --cov-report=html
```

## 📊 Couverture de tests

### Modules testés

| Module | Endpoints | Couverture | Tests |
|--------|-----------|------------|-------|
| **Users** | 12 endpoints | ~95% | 25+ tests |
| **Escrow** | 5 endpoints | ~90% | 20+ tests |
| **Payments** | 6 endpoints | ~85% | 15+ tests |
| **Disputes** | 6 endpoints | ~90% | 18+ tests |
| **Core** | 3 endpoints | ~80% | 10+ tests |
| **Intégration** | Flux E2E | ~100% | 8+ scénarios |

### Analyse de couverture
```bash
# Générer le rapport de couverture
coverage run --source='.' manage.py test
coverage report
coverage html  # Rapport HTML dans htmlcov/
```

## 🧪 Types de tests

### 1. Tests d'authentification (`users/tests.py`)
- ✅ Inscription utilisateur
- ✅ Connexion/Déconnexion
- ✅ Gestion du profil
- ✅ Vérification téléphone (SMS)
- ✅ Upload documents KYC
- ✅ Validation KYC par admin
- ✅ Webhooks Smile ID
- ✅ Permissions par rôle

### 2. Tests Escrow (`escrow/tests.py`)
- ✅ Création de transactions
- ✅ Actions sur transactions (livraison, confirmation)
- ✅ Messages entre parties
- ✅ Statistiques transactions
- ✅ Permissions acheteur/vendeur
- ✅ Validation des montants

### 3. Tests Paiements (`payments/tests.py`)
- ✅ Collecte MTN Mobile Money
- ✅ Collecte Orange Money
- ✅ Webhooks paiements
- ✅ Statut des paiements
- ✅ Historique paiements
- ✅ Méthodes de paiement
- ✅ Permissions et sécurité

### 4. Tests Litiges (`disputes/tests.py`)
- ✅ Création de litiges
- ✅ Assignation d'arbitres
- ✅ Résolution de litiges
- ✅ Upload de preuves
- ✅ Commentaires des parties
- ✅ Statistiques litiges
- ✅ Permissions arbitres

### 5. Tests Core (`core/tests.py`)
- ✅ Health check système
- ✅ Paramètres globaux
- ✅ Logs d'audit
- ✅ Middlewares sécurité
- ✅ Utilitaires core
- ✅ Permissions admin

### 6. Tests d'intégration (`test_integration.py`)
- ✅ Flux transaction complète
- ✅ Résolution de litige E2E
- ✅ Vérification KYC complète
- ✅ Interactions multi-utilisateurs
- ✅ Performance et sécurité

## 🔒 Tests de sécurité

### Authentification & Autorisation
- ✅ Tokens JWT valides/invalides
- ✅ Permissions par rôle (BUYER, SELLER, ARBITRE, ADMIN)
- ✅ Accès aux ressources propres uniquement
- ✅ Protection endpoints sensibles

### Protection des données
- ✅ Validation entrées utilisateur
- ✅ Échappement injections SQL
- ✅ Headers de sécurité
- ✅ Rate limiting (simulation)

### KYC et conformité
- ✅ Validation documents
- ✅ Limites selon statut KYC
- ✅ Vérification Smile ID
- ✅ Audit trail complet

## 📈 Tests de performance

### Optimisation requêtes
- ✅ Nombre de requêtes DB optimisé
- ✅ Use de select_related/prefetch_related
- ✅ Pagination efficace
- ✅ Cache approprié

### Temps de réponse
- ✅ Endpoints < 500ms
- ✅ Health check < 100ms
- ✅ Listes paginées < 1s
- ✅ Upload fichiers < 5s

## 🐛 Tests d'erreurs

### Gestion d'erreurs
- ✅ Données malformées
- ✅ Ressources inexistantes (404)
- ✅ Permissions insuffisantes (403)
- ✅ Erreurs validation (400)
- ✅ Erreurs serveur (500)

### Résilience
- ✅ Services externes indisponibles
- ✅ Timeouts réseau
- ✅ Fichiers corrompus
- ✅ Données incohérentes

## 📊 Métriques de qualité

### Objectifs de couverture
- **Tests unitaires:** > 90%
- **Tests d'intégration:** > 80%
- **Endpoints critiques:** 100%
- **Logique métier:** > 95%

### Standards de qualité
- ✅ Tous les tests passent
- ✅ Temps d'exécution < 5 minutes
- ✅ Aucune dette technique
- ✅ Documentation à jour

## 🔧 Configuration des tests

### Variables d'environnement
```bash
# Base de données de test
DATABASE_URL=sqlite:///test_db.sqlite3

# Mode debug
DEBUG=True

# Clés de test pour services externes
SMILE_ID_SANDBOX=True
MTN_MOMO_SANDBOX=True
ORANGE_MONEY_SANDBOX=True
```

### Données de test
Les tests utilisent des données factices :
- **Utilisateurs:** +237600000000 (admin), +237612345678 (buyer), etc.
- **Montants:** Valeurs en FCFA réalistes
- **Documents:** Images générées automatiquement
- **Webhooks:** Signatures mockées

## 🚨 Résolution des problèmes

### Tests qui échouent
1. **Vérifier la base de données**
   ```bash
   python manage.py migrate
   python manage.py test --keepdb
   ```

2. **Nettoyer le cache**
   ```bash
   python manage.py clear_cache
   python manage.py collectstatic --clear
   ```

3. **Réinstaller les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

### Performance lente
1. **Utiliser keepdb**
   ```bash
   python manage.py test --keepdb
   ```

2. **Tests en parallèle**
   ```bash
   python manage.py test --parallel
   ```

3. **Optimiser les fixtures**
   - Réduire les données de test
   - Utiliser des mocks pour services externes

## 📝 Bonnes pratiques

### Écriture de tests
1. **Noms descriptifs**
   ```python
   def test_buyer_can_create_transaction_with_valid_seller():
   def test_kyc_required_for_large_transactions():
   ```

2. **Arrange-Act-Assert**
   ```python
   # Arrange
   user = create_test_user()
   
   # Act
   response = self.client.post(url, data)
   
   # Assert
   self.assertEqual(response.status_code, 201)
   ```

3. **Isolation des tests**
   - Chaque test est indépendant
   - Nettoyage automatique des données
   - Pas d'effets de bord

### Mocking des services
```python
@patch('payments.services.MTNMoMoService.request_to_pay')
def test_payment_success(self, mock_payment):
    mock_payment.return_value = {'success': True}
    # Test logic here
```

## 📞 Support

Pour toute question sur les tests :
1. Consulter cette documentation
2. Vérifier les logs d'erreur
3. Exécuter `python run_tests.py` pour un diagnostic complet
4. Contacter l'équipe de développement

---

**Dernière mise à jour:** Décembre 2024  
**Version:** 1.0.0  
**Mainteneur:** Équipe Kimi Escrow
