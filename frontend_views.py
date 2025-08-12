"""
Vues Django pour le frontend Kimi Escrow
Avec RBAC et intégration avec l'API DRF
"""

import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.conf import settings
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from functools import wraps
import json

from users.models import KYCDocument
from escrow.models import EscrowTransaction
from disputes.models import Dispute
from frontend_forms import *

User = get_user_model()

# ===== DÉCORATEURS DE PERMISSION ===== #

def role_required(allowed_roles):
    """Décorateur pour vérifier le rôle de l'utilisateur"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
                return redirect('login')
            
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'Profil utilisateur non trouvé.')
                return redirect('login')
            
            if request.user.role not in allowed_roles:
                messages.error(request, 'Vous n\'avez pas les permissions pour accéder à cette page.')
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def kyc_required(view_func):
    """Décorateur pour vérifier le statut KYC"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role != 'ADMIN' and request.user.kyc_status != 'VERIFIED':
            messages.warning(request, 'Vous devez compléter votre vérification KYC pour cette action.')
            return redirect('kyc_status')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ===== UTILITAIRES API ===== #

def get_api_data(request, endpoint, params=None):
    """Fonction utilitaire pour récupérer des données de l'API DRF"""
    try:
        # Construction de l'URL complète
        base_url = getattr(settings, 'API_BASE_URL', 'http://localhost:8000/api')
        url = f"{base_url}{endpoint}"
        
        # Headers avec token d'authentification
        headers = {}
        if request.user.is_authenticated:
            # Ici vous devriez récupérer le token JWT de l'utilisateur
            # Pour la démo, on simule l'API call
            pass
        
        # Pour l'instant, on simule les données au lieu d'appeler l'API
        # En production, vous feriez: response = requests.get(url, headers=headers, params=params)
        return simulate_api_response(endpoint, params)
        
    except Exception as e:
        print(f"Erreur API: {e}")
        return None


def simulate_api_response(endpoint, params=None):
    """Simulation des réponses API pour la démo"""
    # Cette fonction simule les réponses de l'API DRF
    # En production, elle serait remplacée par de vrais appels API
    
    if 'transactions' in endpoint:
        return {
            'success': True,
            'data': {
                'results': [],
                'count': 0,
                'next': None,
                'previous': None
            }
        }
    elif 'disputes' in endpoint:
        return {
            'success': True,
            'data': {
                'results': [],
                'count': 0
            }
        }
    elif 'statistics' in endpoint:
        return {
            'success': True,
            'data': {
                'total_transactions': 0,
                'total_amount': 0,
                'pending_transactions': 0,
                'completed_transactions': 0
            }
        }
    
    return {'success': True, 'data': {}}


# ===== VUES D'AUTHENTIFICATION ===== #

def home(request):
    """Page d'accueil"""
    if request.user.is_authenticated:
        # Rediriger vers le dashboard approprié selon le rôle
        role = request.user.role
        if role == 'BUYER':
            return redirect('buyer_dashboard')
        elif role == 'SELLER':
            return redirect('seller_dashboard')
        elif role == 'ARBITRE':
            return redirect('arbitre_dashboard')
        elif role == 'ADMIN':
            return redirect('admin_dashboard')
    
    return render(request, 'home.html')


@csrf_protect
def register_view(request):
    """Vue d'inscription"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            # Créer l'utilisateur
            user = form.save()
            
            # L'utilisateur est déjà créé avec le rôle dans le formulaire
            
            # Connecter l'utilisateur
            login(request, user)
            
            messages.success(request, 'Inscription réussie! Vérifiez votre téléphone pour le code de vérification.')
            return redirect('verify_phone')
    else:
        form = CustomUserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})


@csrf_protect
def login_view(request):
    """Vue de connexion"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Gérer "Se souvenir de moi"
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)
            
            messages.success(request, f'Bienvenue, {user.first_name}!')
            return redirect('home')
    else:
        form = CustomLoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """Vue de déconnexion"""
    logout(request)
    messages.info(request, 'Vous êtes déconnecté.')
    return redirect('home')


@login_required
@csrf_protect
def verify_phone(request):
    """Vue de vérification de téléphone"""
    if request.user.is_phone_verified:
        messages.info(request, 'Votre téléphone est déjà vérifié.')
        return redirect('home')
    
    if request.method == 'POST':
        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            # Ici vous appelleriez l'API pour vérifier le code
            # Pour la démo, on accepte le code "123456"
            code = form.cleaned_data['verification_code']
            if code == '123456':
                request.user.is_phone_verified = True
                request.user.save()
                messages.success(request, 'Téléphone vérifié avec succès!')
                return redirect('home')
            else:
                messages.error(request, 'Code de vérification incorrect.')
    else:
        form = PhoneVerificationForm()
    
    return render(request, 'users/verify_phone.html', {'form': form})


@login_required
@csrf_protect
def profile_view(request):
    """Vue du profil utilisateur"""
    if request.method == 'POST':
        user_form = ProfileUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileDetailsForm(request.POST, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('profile')
    else:
        user_form = ProfileUpdateForm(instance=request.user)
        profile_form = ProfileDetailsForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'users/profile.html', context)


@login_required
@csrf_protect
def change_password(request):
    """Vue de changement de mot de passe"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password'])
            request.user.save()
            messages.success(request, 'Mot de passe changé avec succès!')
            return redirect('login')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})


# ===== VUES KYC ===== #

@login_required
def kyc_status(request):
    """Vue du statut KYC"""
    documents = KYCDocument.objects.filter(user=request.user)
    
    # Déterminer les documents requis
    required_docs = ['ID_FRONT', 'ID_BACK']
    uploaded_docs = list(documents.values_list('document_type', flat=True))
    missing_docs = [doc for doc in required_docs if doc not in uploaded_docs]
    
    context = {
        'documents': documents,
        'missing_docs': missing_docs,
        'kyc_status': request.user.kyc_status,
    }
    return render(request, 'users/kyc_status.html', context)


@login_required
@csrf_protect
def kyc_upload(request):
    """Vue d'upload de documents KYC"""
    if request.method == 'POST':
        form = KYCDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.save()
            messages.success(request, 'Document uploadé avec succès!')
            return redirect('kyc_status')
    else:
        form = KYCDocumentUploadForm()
    
    return render(request, 'users/kyc_upload.html', {'form': form})


# ===== DASHBOARDS ===== #

@login_required
@role_required(['BUYER'])
def buyer_dashboard(request):
    """Dashboard acheteur"""
    # Récupérer les statistiques via API
    stats_data = get_api_data(request, '/escrow/statistics/')
    
    # Récupérer les transactions récentes
    transactions_data = get_api_data(request, '/escrow/transactions/', {'limit': 5})
    
    context = {
        'stats': stats_data.get('data', {}) if stats_data else {},
        'recent_transactions': transactions_data.get('data', {}).get('results', []) if transactions_data else [],
    }
    return render(request, 'dashboards/buyer_dashboard.html', context)


@login_required
@role_required(['SELLER'])
def seller_dashboard(request):
    """Dashboard vendeur"""
    # Récupérer les statistiques de vente
    stats_data = get_api_data(request, '/escrow/statistics/')
    
    # Récupérer les commandes récentes
    transactions_data = get_api_data(request, '/escrow/transactions/', {'limit': 5})
    
    context = {
        'stats': stats_data.get('data', {}) if stats_data else {},
        'recent_orders': transactions_data.get('data', {}).get('results', []) if transactions_data else [],
    }
    return render(request, 'dashboards/seller_dashboard.html', context)


@login_required
@role_required(['ARBITRE'])
def arbitre_dashboard(request):
    """Dashboard arbitre"""
    # Récupérer les litiges assignés
    disputes_data = get_api_data(request, '/disputes/', {'arbitre': request.user.id})
    
    context = {
        'assigned_disputes': disputes_data.get('data', {}).get('results', []) if disputes_data else [],
    }
    return render(request, 'dashboards/arbitre_dashboard.html', context)


@login_required
@role_required(['ADMIN'])
def admin_dashboard(request):
    """Dashboard administrateur"""
    # Récupérer les statistiques globales
    user_stats = get_api_data(request, '/auth/admin/statistics/')
    transaction_stats = get_api_data(request, '/escrow/statistics/')
    dispute_stats = get_api_data(request, '/disputes/admin/statistics/')
    
    context = {
        'user_stats': user_stats.get('data', {}) if user_stats else {},
        'transaction_stats': transaction_stats.get('data', {}) if transaction_stats else {},
        'dispute_stats': dispute_stats.get('data', {}) if dispute_stats else {},
    }
    return render(request, 'dashboards/admin_dashboard.html', context)


# ===== VUES TRANSACTIONS ===== #

@login_required
@role_required(['BUYER'])
@kyc_required
@csrf_protect
def transaction_create(request):
    """Créer une nouvelle transaction"""
    if request.method == 'POST':
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            # Ici vous appelleriez l'API pour créer la transaction
            # Pour la démo, on simule la création
            messages.success(request, 'Transaction créée avec succès!')
            return redirect('buyer_transactions')
    else:
        form = TransactionCreateForm()
    
    return render(request, 'escrow/transaction_create.html', {'form': form})


@login_required
def buyer_transactions(request):
    """Liste des transactions de l'acheteur"""
    # Filtres
    form = TransactionFilterForm(request.GET)
    filters = {}
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v}
    
    # Récupérer les transactions via API
    transactions_data = get_api_data(request, '/escrow/transactions/', filters)
    transactions = transactions_data.get('data', {}).get('results', []) if transactions_data else []
    
    # Pagination
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'transactions': page_obj,
        'filter_form': form,
    }
    return render(request, 'escrow/buyer_transactions.html', context)


@login_required
def seller_transactions(request):
    """Liste des transactions du vendeur"""
    # Filtres
    form = TransactionFilterForm(request.GET)
    filters = {}
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v}
    
    # Récupérer les transactions via API
    transactions_data = get_api_data(request, '/escrow/transactions/', filters)
    transactions = transactions_data.get('data', {}).get('results', []) if transactions_data else []
    
    context = {
        'transactions': transactions,
        'filter_form': form,
    }
    return render(request, 'escrow/seller_transactions.html', context)


@login_required
def transaction_detail(request, transaction_id):
    """Détail d'une transaction"""
    # Récupérer la transaction via API
    transaction_data = get_api_data(request, f'/escrow/transactions/{transaction_id}/')
    
    if not transaction_data or not transaction_data.get('success'):
        raise Http404("Transaction non trouvée")
    
    transaction = transaction_data.get('data', {})
    
    # Récupérer les messages de la transaction
    messages_data = get_api_data(request, f'/escrow/transactions/{transaction_id}/messages/')
    messages_list = messages_data.get('data', {}).get('results', []) if messages_data else []
    
    # Formulaires
    action_form = TransactionActionForm()
    message_form = TransactionMessageForm()
    
    context = {
        'transaction': transaction,
        'messages': messages_list,
        'action_form': action_form,
        'message_form': message_form,
    }
    return render(request, 'escrow/transaction_detail.html', context)


# ===== VUES PAIEMENTS ===== #

@login_required
def payment_methods(request):
    """Liste des méthodes de paiement"""
    # Récupérer les méthodes via API
    methods_data = get_api_data(request, '/payments/methods/')
    methods = methods_data.get('data', []) if methods_data else []
    
    return render(request, 'payments/payment_methods.html', {'methods': methods})


@login_required
def payment_history(request):
    """Historique des paiements"""
    # Récupérer l'historique via API
    history_data = get_api_data(request, '/payments/history/')
    payments = history_data.get('data', {}).get('results', []) if history_data else []
    
    return render(request, 'payments/payment_history.html', {'payments': payments})


# ===== VUES LITIGES ===== #

@login_required
@csrf_protect
def dispute_create(request):
    """Créer un litige"""
    transaction_id = request.GET.get('transaction')
    
    if request.method == 'POST':
        form = DisputeCreateForm(request.POST)
        if form.is_valid():
            # Ici vous appelleriez l'API pour créer le litige
            messages.success(request, 'Litige créé avec succès!')
            return redirect('buyer_disputes')
    else:
        form = DisputeCreateForm()
    
    context = {
        'form': form,
        'transaction_id': transaction_id,
    }
    return render(request, 'disputes/dispute_create.html', context)


@login_required
def buyer_disputes(request):
    """Liste des litiges de l'acheteur"""
    # Récupérer les litiges via API
    disputes_data = get_api_data(request, '/disputes/', {'plaintiff': request.user.id})
    disputes = disputes_data.get('data', {}).get('results', []) if disputes_data else []
    
    return render(request, 'disputes/buyer_disputes.html', {'disputes': disputes})


@login_required
def seller_disputes(request):
    """Liste des litiges du vendeur"""
    # Récupérer les litiges via API
    disputes_data = get_api_data(request, '/disputes/', {'defendant': request.user.id})
    disputes = disputes_data.get('data', {}).get('results', []) if disputes_data else []
    
    return render(request, 'disputes/seller_disputes.html', {'disputes': disputes})


@login_required
@role_required(['ARBITRE'])
def arbitre_disputes(request):
    """Liste des litiges pour l'arbitre"""
    # Récupérer les litiges assignés via API
    disputes_data = get_api_data(request, '/disputes/', {'arbitre': request.user.id})
    disputes = disputes_data.get('data', {}).get('results', []) if disputes_data else []
    
    return render(request, 'disputes/arbitre_disputes.html', {'disputes': disputes})


@login_required
def dispute_detail(request, dispute_id):
    """Détail d'un litige"""
    # Récupérer le litige via API
    dispute_data = get_api_data(request, f'/disputes/{dispute_id}/')
    
    if not dispute_data or not dispute_data.get('success'):
        raise Http404("Litige non trouvé")
    
    dispute = dispute_data.get('data', {})
    
    # Récupérer les preuves et commentaires
    evidence_data = get_api_data(request, f'/disputes/{dispute_id}/evidence/')
    comments_data = get_api_data(request, f'/disputes/{dispute_id}/comments/')
    
    evidence = evidence_data.get('data', []) if evidence_data else []
    comments = comments_data.get('data', []) if comments_data else []
    
    # Formulaires
    evidence_form = DisputeEvidenceForm()
    comment_form = DisputeCommentForm()
    resolution_form = DisputeResolutionForm() if request.user.role == 'ARBITRE' else None
    
    context = {
        'dispute': dispute,
        'evidence': evidence,
        'comments': comments,
        'evidence_form': evidence_form,
        'comment_form': comment_form,
        'resolution_form': resolution_form,
    }
    return render(request, 'disputes/dispute_detail.html', context)


# ===== VUES ADMIN ===== #

@login_required
@role_required(['ADMIN'])
def admin_users(request):
    """Gestion des utilisateurs (admin)"""
    # Filtres de recherche
    form = AdminUserSearchForm(request.GET)
    filters = {}
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v}
    
    # Récupérer les utilisateurs via API
    users_data = get_api_data(request, '/auth/admin/users/', filters)
    users = users_data.get('data', {}).get('results', []) if users_data else []
    
    context = {
        'users': users,
        'search_form': form,
    }
    return render(request, 'admin/users.html', context)


@login_required
@role_required(['ADMIN'])
def admin_kyc_pending(request):
    """KYC en attente d'approbation"""
    # Récupérer les KYC en attente
    pending_kyc = KYCDocument.objects.filter(status='PENDING').select_related('user')
    
    return render(request, 'admin/kyc_pending.html', {'pending_kyc': pending_kyc})


@login_required
@role_required(['ADMIN'])
@csrf_protect
def admin_kyc_approve(request, user_id):
    """Approuver/rejeter un KYC"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminKYCApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data['notes']
            
            if action == 'approve':
                user.kyc_status = 'VERIFIED'
                messages.success(request, f'KYC approuvé pour {user.get_full_name()}')
            else:
                user.kyc_status = 'REJECTED'
                messages.info(request, f'KYC rejeté pour {user.get_full_name()}')
            
            user.save()
            return redirect('admin_kyc_pending')
    else:
        form = AdminKYCApprovalForm()
    
    context = {
        'user': user,
        'form': form,
        'documents': KYCDocument.objects.filter(user=user)
    }
    return render(request, 'admin/kyc_approve.html', context)


# ===== VUES AJAX ===== #

@login_required
@require_http_methods(["POST"])
def ajax_transaction_action(request, transaction_id):
    """Action AJAX sur une transaction"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        notes = data.get('notes', '')
        
        # Ici vous appelleriez l'API pour effectuer l'action
        # Pour la démo, on simule le succès
        
        return JsonResponse({
            'success': True,
            'message': f'Action "{action}" effectuée avec succès!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@require_http_methods(["POST"])
def ajax_send_message(request, transaction_id):
    """Envoyer un message AJAX"""
    try:
        data = json.loads(request.body)
        message = data.get('message')
        
        if not message:
            return JsonResponse({
                'success': False,
                'message': 'Le message ne peut pas être vide'
            })
        
        # Ici vous appelleriez l'API pour envoyer le message
        # Pour la démo, on simule le succès
        
        return JsonResponse({
            'success': True,
            'message': 'Message envoyé avec succès!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
def ajax_payment_status(request, payment_reference):
    """Vérifier le statut d'un paiement en AJAX"""
    try:
        # Ici vous appelleriez l'API pour vérifier le statut
        # Pour la démo, on simule une réponse
        
        return JsonResponse({
            'success': True,
            'data': {
                'reference': payment_reference,
                'status': 'PENDING',
                'amount': '150000'
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# ===== RÉINITIALISATION DE MOT DE PASSE ===== #

def password_reset(request):
    """Page de réinitialisation de mot de passe"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            # Ici vous implémenteriez la logique de réinitialisation
            # Pour l'instant, on simule le succès
            messages.success(request, 'Un SMS de réinitialisation a été envoyé à votre numéro de téléphone.')
            return redirect('login')
    else:
        form = PasswordResetForm()
    
    return render(request, 'users/password_reset.html', {'form': form})


def password_reset_confirm(request, uidb64, token):
    """Confirmation de réinitialisation de mot de passe"""
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            # Ici vous implémenteriez la logique de confirmation
            # Pour l'instant, on simule le succès
            messages.success(request, 'Votre mot de passe a été modifié avec succès.')
            return redirect('login')
    else:
        form = SetPasswordForm()
    
    return render(request, 'users/password_reset_confirm.html', {'form': form})
