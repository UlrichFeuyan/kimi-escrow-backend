# 🎨 Frontend Kimi Escrow - Guide Complet

## 📋 Vue d'ensemble

Ce frontend Django complet intègre parfaitement le backend Django REST Framework existant pour créer une expérience utilisateur moderne et sécurisée. Le frontend utilise Django Templates avec Bootstrap 5, JavaScript vanilla et un système RBAC (Role-Based Access Control) complet.

## 🏗️ Architecture Frontend

### Structure des fichiers
```
kimi-escrow-backend/
├── templates/                          # Templates Django
│   ├── base.html                      # Template de base avec Bootstrap 5
│   ├── home.html                      # Page d'accueil
│   ├── includes/                      # Composants réutilisables
│   │   ├── header.html               # Navigation principale
│   │   ├── footer.html               # Pied de page
│   │   ├── navbar_buyer.html         # Menu acheteur
│   │   ├── navbar_seller.html        # Menu vendeur
│   │   ├── navbar_arbitre.html       # Menu arbitre
│   │   └── navbar_admin.html         # Menu administrateur
│   ├── users/                        # Templates utilisateurs
│   │   ├── login.html               # Connexion
│   │   ├── register.html            # Inscription
│   │   ├── profile.html             # Profil utilisateur
│   │   └── kyc_upload.html          # Upload documents KYC
│   ├── dashboards/                   # Dashboards par rôle
│   │   ├── buyer_dashboard.html     # Dashboard acheteur
│   │   ├── seller_dashboard.html    # Dashboard vendeur
│   │   ├── arbitre_dashboard.html   # Dashboard arbitre
│   │   └── admin_dashboard.html     # Dashboard admin
│   ├── escrow/                       # Templates transactions
│   │   ├── transaction_create.html  # Créer transaction
│   │   ├── transaction_detail.html  # Détail transaction
│   │   └── transaction_list.html    # Liste transactions
│   ├── payments/                     # Templates paiements
│   │   ├── payment_methods.html     # Méthodes de paiement
│   │   └── payment_history.html     # Historique paiements
│   └── disputes/                     # Templates litiges
│       ├── dispute_create.html      # Créer litige
│       └── dispute_detail.html      # Détail litige
├── static/                           # Fichiers statiques
│   ├── css/
│   │   └── main.css                 # Styles personnalisés
│   ├── js/
│   │   └── main.js                  # JavaScript principal avec AJAX
│   └── images/                      # Images et icônes
├── frontend_forms.py                 # Formulaires Django avec validation
├── frontend_views.py                 # Vues Django pour les templates
├── frontend_urls.py                  # URLs du frontend
└── FRONTEND_README.md               # Ce fichier
```

## 🎯 Fonctionnalités par Rôle

### 👤 BUYER (Acheteur)
- **Dashboard**: Statistiques d'achats, transactions récentes
- **Transactions**: Créer, lister, voir détails, payer
- **Paiements**: Mobile Money (MTN/Orange), historique
- **Litiges**: Créer, suivre, ajouter preuves
- **Profil**: Mise à jour infos, KYC, changement mot de passe

### 🏪 SELLER (Vendeur)
- **Dashboard**: Commandes reçues, revenus, performance
- **Ventes**: Accepter commandes, marquer livré, preuves livraison
- **Revenus**: Historique paiements reçus, statistiques
- **Litiges**: Répondre aux litiges, fournir preuves
- **Profil**: Gestion réputation, KYC vendeur

### ⚖️ ARBITRE (Arbitre)
- **Dashboard**: Litiges assignés, charge de travail
- **Arbitrage**: Examiner preuves, prendre décisions
- **Résolutions**: Remboursements partiels/complets
- **Statistiques**: Performance d'arbitrage
- **Planning**: Disponibilités, cases assignées

### 👨‍💼 ADMIN (Administrateur)
- **Dashboard**: Vue d'ensemble système, métriques globales
- **Utilisateurs**: CRUD utilisateurs, approbation KYC
- **Transactions**: Monitoring, intervention si nécessaire
- **Litiges**: Assignation arbitres, escalade
- **Système**: Logs audit, paramètres globaux, santé système

## 🔐 Sécurité et RBAC

### Protection CSRF
Tous les formulaires incluent la protection CSRF Django :
```html
<form method="post">
    {% csrf_token %}
    <!-- Formulaire -->
</form>
```

### Contrôle d'accès par rôle
```python
# Décorateur de permission
@role_required(['BUYER', 'SELLER'])
def some_view(request):
    # Accessible uniquement aux acheteurs et vendeurs
    pass

# Vérification KYC
@kyc_required
def kyc_protected_view(request):
    # Accessible uniquement aux utilisateurs KYC vérifiés
    pass
```

### Navigation adaptative
Les menus s'adaptent automatiquement au rôle :
```html
{% if user.profile.role == 'BUYER' %}
    {% include 'includes/navbar_buyer.html' %}
{% elif user.profile.role == 'SELLER' %}
    {% include 'includes/navbar_seller.html' %}
{% endif %}
```

## 📡 Intégration avec l'API DRF

### Configuration JavaScript
```javascript
const KimiEscrow = {
    apiBaseUrl: '/api',
    csrfToken: '{{ csrf_token }}',
    currentUser: {
        id: {{ user.id }},
        role: '{{ user.profile.role }}',
        isAuthenticated: {{ user.is_authenticated|yesno:"true,false" }}
    },
    endpoints: {
        escrow: {
            transactions: '/api/escrow/transactions/',
            transactionDetail: (id) => `/api/escrow/transactions/${id}/`,
            // ... autres endpoints
        }
    }
};
```

### Fonction AJAX générique
```javascript
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': KimiEscrow.csrfToken,
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        credentials: 'include'
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    return await response.json();
}
```

### Exemples d'utilisation
```javascript
// Charger les transactions
const transactions = await apiRequest('/api/escrow/transactions/');

// Créer une transaction
const newTransaction = await apiRequest('/api/escrow/transactions/', {
    method: 'POST',
    body: JSON.stringify(transactionData)
});

// Effectuer une action sur transaction
await apiRequest(`/api/escrow/transactions/${id}/actions/`, {
    method: 'POST',
    body: JSON.stringify({ action: 'mark_delivered' })
});
```

## 💳 Paiements Mobile Money

### Interface utilisateur
- Sélection automatique du provider (MTN/Orange)
- Formatage automatique du numéro
- Validation en temps réel
- Suivi du statut de paiement

### Workflow JavaScript
```javascript
// 1. Initier paiement
const payment = await apiRequest('/api/payments/momo/collect/', {
    method: 'POST',
    body: JSON.stringify({
        transaction_id: transactionId,
        phone_number: phoneNumber,
        provider: 'MTN_MOMO',
        amount: amount
    })
});

// 2. Suivre le statut
function checkPaymentStatus(reference) {
    setInterval(async () => {
        const status = await apiRequest(`/api/payments/momo/status/${reference}/`);
        if (status.data.status === 'COMPLETED') {
            showSuccess('Paiement confirmé!');
            reloadTransactions();
        }
    }, 5000);
}
```

## 🎨 Design et UX

### Bootstrap 5 + CSS Custom
- Design responsive mobile-first
- Thème cohérent avec couleurs de marque
- Animations et transitions fluides
- Loading states et feedback utilisateur

### Composants réutilisables
```css
/* Cartes statistiques */
.stats-card {
    transition: all 0.3s ease;
    border-left: 4px solid var(--primary-color);
}

/* Badges de statut */
.status-pending { background-color: var(--warning-color); }
.status-completed { background-color: var(--success-color); }

/* Timeline d'activité */
.timeline-item::before {
    content: '';
    position: absolute;
    background-color: var(--primary-color);
    border-radius: 50%;
}
```

### Notifications et alertes
```javascript
function showAlert(message, type = 'info', duration = 5000) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show">
            <i class="bi bi-${getAlertIcon(type)}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    // Auto-dismiss après durée spécifiée
}
```

## 📁 Formulaires Django

### Validation côté serveur
```python
class TransactionCreateForm(forms.ModelForm):
    def clean_seller_phone(self):
        seller_phone = self.cleaned_data['seller_phone']
        try:
            User.objects.get(phone_number=seller_phone)
        except User.DoesNotExist:
            raise ValidationError('Aucun vendeur trouvé avec ce numéro.')
        return seller_phone
    
    def clean(self):
        cleaned_data = super().clean()
        # Validation cross-field
        return cleaned_data
```

### Widgets personnalisés
```python
amount = forms.DecimalField(
    widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '150000',
        'min': '1000',
        'step': '1000'
    }),
    help_text='Montant minimum: 1,000 FCFA'
)
```

## 🚀 Déploiement et Configuration

### 1. Configuration Django
```python
# settings.py
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
```

### 2. URLs principales
```python
# kimi_escrow/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api_urls')),  # API DRF existante
    path('', include('frontend_urls')),  # Frontend Django
]
```

### 3. Collecte des fichiers statiques
```bash
python manage.py collectstatic
```

## 🔧 Développement

### Structure des vues
```python
@login_required
@role_required(['BUYER'])
def transaction_create(request):
    if request.method == 'POST':
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            # Appel à l'API DRF pour créer
            api_data = call_api('POST', '/api/escrow/transactions/', form.cleaned_data)
            if api_data['success']:
                messages.success(request, 'Transaction créée!')
                return redirect('buyer_dashboard')
    else:
        form = TransactionCreateForm()
    
    return render(request, 'escrow/transaction_create.html', {'form': form})
```

### Tests frontend
```python
# tests_frontend.py
class FrontendTestCase(TestCase):
    def test_buyer_dashboard_access(self):
        # Test d'accès au dashboard acheteur
        self.client.login(username='buyer', password='pass')
        response = self.client.get('/dashboard/buyer/')
        self.assertEqual(response.status_code, 200)
    
    def test_role_based_navigation(self):
        # Test navigation adaptée au rôle
        response = self.client.get('/')
        self.assertContains(response, 'navbar_buyer.html')
```

## 📊 Monitoring et Analytics

### Métriques frontend
- Temps de chargement des pages
- Taux de conversion des formulaires
- Utilisation des fonctionnalités par rôle
- Erreurs JavaScript et API

### Logs d'audit
Toutes les actions critiques sont loggées :
```python
# Exemple dans frontend_views.py
def transaction_create(request):
    # ... logique ...
    if form.is_valid():
        # Log de l'action
        AuditLog.objects.create(
            user=request.user,
            action='TRANSACTION_CREATED',
            details=f'Transaction {transaction.id} créée'
        )
```

## 🔧 Maintenance

### Mise à jour des dépendances
```bash
# Mettre à jour Bootstrap
# Modifier les CDN dans base.html

# Mettre à jour les icônes Bootstrap
# Vérifier la compatibilité des classes CSS
```

### Optimisations
- Minification CSS/JS en production
- Compression des images
- Lazy loading des composants
- Cache des requêtes API côté frontend

## 🆘 Support et Documentation

### Ressources utiles
- [Documentation Django Templates](https://docs.djangoproject.com/en/4.2/topics/templates/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [Django Forms](https://docs.djangoproject.com/en/4.2/topics/forms/)

### Contact équipe
Pour toute question sur le frontend :
- 📧 Email: dev-frontend@kimiescrow.cm
- 💬 Slack: #frontend-kimi
- 📚 Wiki: confluence.kimiescrow.cm/frontend

---

**🎉 Frontend Kimi Escrow - Développé avec ❤️ pour une expérience utilisateur exceptionnelle**
