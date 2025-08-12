"""
Formulaires Django pour le frontend Kimi Escrow
Avec validation CSRF et sécurité intégrée
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from users.models import UserProfile, KYCDocument
from escrow.models import EscrowTransaction
from disputes.models import Dispute, DisputeEvidence
import re

User = get_user_model()

# ===== FORMULAIRES D'AUTHENTIFICATION ===== #

class CustomUserRegistrationForm(UserCreationForm):
    """Formulaire d'inscription personnalisé"""
    
    phone_number = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+237[6-9]\d{8}$',
                message='Format: +237XXXXXXXXX (numéro camerounais valide)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237XXXXXXXXX'
        }),
        label='Numéro de téléphone'
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre prénom'
        }),
        label='Prénom'
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom'
        }),
        label='Nom'
    )
    
    role = forms.ChoiceField(
        choices=[
            ('BUYER', 'Acheteur'),
            ('SELLER', 'Vendeur'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Je veux'
    )
    
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe sécurisé'
        }),
        help_text='Au moins 8 caractères avec majuscules, minuscules et chiffres'
    )
    
    password2 = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Répétez le mot de passe'
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='J\'accepte les conditions d\'utilisation et la politique de confidentialité'
    )
    
    class Meta:
        model = User
        fields = ('phone_number', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError('Ce numéro de téléphone est déjà utilisé.')
        return phone_number
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            # Validation mot de passe complexe
            if len(password) < 8:
                raise ValidationError('Le mot de passe doit contenir au moins 8 caractères.')
            if not re.search(r'[A-Z]', password):
                raise ValidationError('Le mot de passe doit contenir au moins une majuscule.')
            if not re.search(r'[a-z]', password):
                raise ValidationError('Le mot de passe doit contenir au moins une minuscule.')
            if not re.search(r'\d', password):
                raise ValidationError('Le mot de passe doit contenir au moins un chiffre.')
        return password


class CustomLoginForm(AuthenticationForm):
    """Formulaire de connexion personnalisé"""
    
    username = forms.CharField(
        label='Numéro de téléphone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237XXXXXXXXX'
        })
    )
    
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre mot de passe'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Se souvenir de moi'
    )


class PhoneVerificationForm(forms.Form):
    """Formulaire de vérification de téléphone"""
    
    verification_code = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='Le code doit contenir exactement 6 chiffres'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '000000',
            'maxlength': '6'
        }),
        label='Code de vérification'
    )


class ProfileUpdateForm(forms.ModelForm):
    """Formulaire de mise à jour du profil"""
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Prénom'
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nom'
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com'
        }),
        label='Email (optionnel)'
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class ProfileDetailsForm(forms.ModelForm):
    """Formulaire pour les détails du profil"""
    
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ville, Quartier'
        }),
        label='Localisation'
    )
    
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Parlez de vous...'
        }),
        label='Biographie'
    )
    
    class Meta:
        model = UserProfile
        fields = ('location', 'bio')


class PasswordChangeForm(forms.Form):
    """Formulaire de changement de mot de passe"""
    
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe actuel'
        }),
        label='Mot de passe actuel'
    )
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe'
        }),
        label='Nouveau mot de passe',
        help_text='Au moins 8 caractères avec majuscules, minuscules et chiffres'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le nouveau mot de passe'
        }),
        label='Confirmer le mot de passe'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data['old_password']
        if not self.user.check_password(old_password):
            raise ValidationError('Mot de passe actuel incorrect.')
        return old_password
    
    def clean_confirm_password(self):
        new_password = self.cleaned_data.get('new_password')
        confirm_password = self.cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('Les mots de passe ne correspondent pas.')
        return confirm_password


# ===== FORMULAIRES KYC ===== #

class KYCDocumentUploadForm(forms.ModelForm):
    """Formulaire d'upload de documents KYC"""
    
    DOCUMENT_CHOICES = [
        ('ID_FRONT', 'Carte d\'identité (recto)'),
        ('ID_BACK', 'Carte d\'identité (verso)'),
        ('PASSPORT', 'Passeport'),
        ('DRIVING_LICENSE', 'Permis de conduire'),
        ('UTILITY_BILL', 'Facture de service public'),
    ]
    
    document_type = forms.ChoiceField(
        choices=DOCUMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Type de document'
    )
    
    file = forms.FileField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])
        ],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.jpg,.jpeg,.png,.pdf'
        }),
        label='Fichier',
        help_text='Formats acceptés: JPG, PNG, PDF (max 5MB)'
    )
    
    class Meta:
        model = KYCDocument
        fields = ('document_type', 'file')
    
    def clean_file(self):
        file = self.cleaned_data['file']
        if file:
            if file.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError('Le fichier ne doit pas dépasser 5MB.')
        return file


# ===== FORMULAIRES TRANSACTIONS ===== #

class TransactionCreateForm(forms.ModelForm):
    """Formulaire de création de transaction"""
    
    CATEGORY_CHOICES = [
        ('GOODS', 'Biens physiques'),
        ('SERVICES', 'Services'),
        ('DIGITAL', 'Produits numériques'),
    ]
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: iPhone 13 Pro Max 256GB'
        }),
        label='Titre de la transaction'
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Décrivez en détail ce que vous achetez...'
        }),
        label='Description détaillée'
    )
    
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Catégorie'
    )
    
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '150000',
            'min': '1000',
            'step': '1000'
        }),
        label='Montant (FCFA)',
        help_text='Montant minimum: 1,000 FCFA'
    )
    
    seller_phone = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+237[6-9]\d{8}$',
                message='Numéro camerounais valide requis'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237XXXXXXXXX'
        }),
        label='Numéro du vendeur'
    )
    
    delivery_address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Adresse complète de livraison'
        }),
        label='Adresse de livraison'
    )
    
    payment_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Délai de paiement',
        help_text='Date limite pour effectuer le paiement'
    )
    
    delivery_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Délai de livraison',
        help_text='Date limite pour la livraison'
    )
    
    class Meta:
        model = EscrowTransaction
        fields = ('title', 'description', 'category', 'amount', 'seller_phone', 
                 'delivery_address', 'payment_deadline', 'delivery_deadline')
    
    def clean_seller_phone(self):
        seller_phone = self.cleaned_data['seller_phone']
        try:
            User.objects.get(phone_number=seller_phone)
        except User.DoesNotExist:
            raise ValidationError('Aucun vendeur trouvé avec ce numéro.')
        return seller_phone
    
    def clean(self):
        cleaned_data = super().clean()
        payment_deadline = cleaned_data.get('payment_deadline')
        delivery_deadline = cleaned_data.get('delivery_deadline')
        
        if payment_deadline and delivery_deadline:
            if payment_deadline >= delivery_deadline:
                raise ValidationError('Le délai de paiement doit être antérieur au délai de livraison.')
        
        return cleaned_data


class TransactionActionForm(forms.Form):
    """Formulaire pour les actions sur les transactions"""
    
    ACTION_CHOICES = [
        ('mark_delivered', 'Marquer comme livré'),
        ('confirm_delivery', 'Confirmer la réception'),
        ('cancel', 'Annuler la transaction'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Action'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notes ou commentaires (optionnel)...'
        }),
        label='Notes'
    )


class TransactionMessageForm(forms.Form):
    """Formulaire pour les messages de transaction"""
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tapez votre message...'
        }),
        label='Message',
        max_length=1000
    )


# ===== FORMULAIRES PAIEMENTS ===== #

class PaymentForm(forms.Form):
    """Formulaire de paiement Mobile Money"""
    
    PROVIDER_CHOICES = [
        ('MTN_MOMO', 'MTN Mobile Money'),
        ('ORANGE_MONEY', 'Orange Money'),
    ]
    
    phone_number = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+237[6-9]\d{8}$',
                message='Numéro camerounais valide requis'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237XXXXXXXXX'
        }),
        label='Numéro de paiement'
    )
    
    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Méthode de paiement'
    )
    
    confirm_amount = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Je confirme le montant à payer'
    )


# ===== FORMULAIRES LITIGES ===== #

class DisputeCreateForm(forms.ModelForm):
    """Formulaire de création de litige"""
    
    REASON_CHOICES = [
        ('PRODUCT_NOT_AS_DESCRIBED', 'Produit non conforme à la description'),
        ('NOT_DELIVERED', 'Non livré'),
        ('DAMAGED_PRODUCT', 'Produit endommagé'),
        ('BUYER_NOT_RESPONDING', 'Acheteur ne répond plus'),
        ('PAYMENT_ISSUE', 'Problème de paiement'),
        ('OTHER', 'Autre raison'),
    ]
    
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Motif du litige'
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Expliquez en détail le problème rencontré...'
        }),
        label='Description du problème'
    )
    
    amount_disputed = forms.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1000'
        }),
        label='Montant contesté (FCFA)',
        help_text='Montant que vous souhaitez récupérer'
    )
    
    class Meta:
        model = Dispute
        fields = ('reason', 'description', 'amount_disputed')


class DisputeEvidenceForm(forms.ModelForm):
    """Formulaire d'ajout de preuve pour litige"""
    
    EVIDENCE_CHOICES = [
        ('PHOTO', 'Photo'),
        ('DOCUMENT', 'Document'),
        ('VIDEO', 'Vidéo'),
        ('SCREENSHOT', 'Capture d\'écran'),
    ]
    
    evidence_type = forms.ChoiceField(
        choices=EVIDENCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Type de preuve'
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Décrivez cette preuve...'
        }),
        label='Description'
    )
    
    file = forms.FileField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'mp4', 'mov'])
        ],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.jpg,.jpeg,.png,.pdf,.mp4,.mov'
        }),
        label='Fichier',
        help_text='Formats: JPG, PNG, PDF, MP4, MOV (max 10MB)'
    )
    
    class Meta:
        model = DisputeEvidence
        fields = ('evidence_type', 'description', 'file')
    
    def clean_file(self):
        file = self.cleaned_data['file']
        if file:
            if file.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError('Le fichier ne doit pas dépasser 10MB.')
        return file


class DisputeCommentForm(forms.Form):
    """Formulaire de commentaire pour litige"""
    
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ajoutez votre commentaire...'
        }),
        label='Commentaire',
        max_length=1000
    )


class DisputeResolutionForm(forms.Form):
    """Formulaire de résolution de litige (pour arbitres)"""
    
    RESOLUTION_CHOICES = [
        ('BUYER_WINS', 'Donner raison à l\'acheteur'),
        ('SELLER_WINS', 'Donner raison au vendeur'),
        ('PARTIAL_REFUND', 'Remboursement partiel'),
    ]
    
    resolution = forms.ChoiceField(
        choices=RESOLUTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Décision'
    )
    
    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Justifiez votre décision...'
        }),
        label='Justification de la décision'
    )
    
    refund_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1000'
        }),
        label='Montant du remboursement (FCFA)',
        help_text='Requis pour remboursement partiel'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        resolution = cleaned_data.get('resolution')
        refund_amount = cleaned_data.get('refund_amount')
        
        if resolution == 'PARTIAL_REFUND' and not refund_amount:
            raise ValidationError('Le montant du remboursement est requis pour un remboursement partiel.')
        
        return cleaned_data


# ===== FORMULAIRES ADMIN ===== #

class AdminKYCApprovalForm(forms.Form):
    """Formulaire d'approbation KYC par l'admin"""
    
    ACTION_CHOICES = [
        ('approve', 'Approuver'),
        ('reject', 'Rejeter'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Action'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notes sur la décision (optionnel)...'
        }),
        label='Notes'
    )


class AdminUserSearchForm(forms.Form):
    """Formulaire de recherche d'utilisateurs pour l'admin"""
    
    ROLE_CHOICES = [
        ('', 'Tous les rôles'),
        ('BUYER', 'Acheteurs'),
        ('SELLER', 'Vendeurs'),
        ('ARBITRE', 'Arbitres'),
        ('ADMIN', 'Administrateurs'),
    ]
    
    KYC_STATUS_CHOICES = [
        ('', 'Tous les statuts'),
        ('PENDING', 'En attente'),
        ('VERIFIED', 'Vérifiés'),
        ('REJECTED', 'Rejetés'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, téléphone...'
        }),
        label='Recherche'
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Rôle'
    )
    
    kyc_status = forms.ChoiceField(
        choices=KYC_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Statut KYC'
    )


# ===== FORMULAIRES DE FILTRAGE ===== #

class TransactionFilterForm(forms.Form):
    """Formulaire de filtrage des transactions"""
    
    STATUS_CHOICES = [
        ('', 'Tous les statuts'),
        ('PENDING', 'En attente'),
        ('PAYMENT_PENDING', 'Paiement en attente'),
        ('PAYMENT_CONFIRMED', 'Paiement confirmé'),
        ('DELIVERED', 'Livré'),
        ('COMPLETED', 'Terminé'),
        ('CANCELLED', 'Annulé'),
        ('DISPUTED', 'En litige'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher...'
        }),
        label='Recherche'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select status-filter'}),
        label='Statut'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Du'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Au'
    )

# ===== FORMULAIRES DE RÉINITIALISATION DE MOT DE PASSE ===== #

class PasswordResetForm(forms.Form):
    """Formulaire de réinitialisation de mot de passe"""
    
    phone_number = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+237[6-9]\d{8}$',
                message='Format: +237XXXXXXXXX (numéro camerounais valide)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237XXXXXXXXX'
        }),
        label='Numéro de téléphone'
    )
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError('Aucun compte associé à ce numéro de téléphone.')
        return phone_number


class SetPasswordForm(forms.Form):
    """Formulaire de définition d'un nouveau mot de passe"""
    
    new_password1 = forms.CharField(
        label='Nouveau mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe sécurisé'
        }),
        help_text='Au moins 8 caractères avec majuscules, minuscules et chiffres'
    )
    
    new_password2 = forms.CharField(
        label='Confirmer le nouveau mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Répétez le nouveau mot de passe'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('Les deux mots de passe ne correspondent pas.')
            
            if len(password1) < 8:
                raise ValidationError('Le mot de passe doit contenir au moins 8 caractères.')
            
            if not re.search(r'[A-Z]', password1):
                raise ValidationError('Le mot de passe doit contenir au moins une majuscule.')
            
            if not re.search(r'[a-z]', password1):
                raise ValidationError('Le mot de passe doit contenir au moins une minuscule.')
            
            if not re.search(r'\d', password1):
                raise ValidationError('Le mot de passe doit contenir au moins un chiffre.')
        
        return cleaned_data
