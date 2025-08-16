from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission personnalisée pour permettre seulement aux propriétaires d'un objet de le modifier.
    """
    def has_object_permission(self, request, view, obj):
        # Permissions de lecture pour toutes les requêtes.
        # Nous autorisons toujours les requêtes GET, HEAD ou OPTIONS.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permissions d'écriture seulement pour le propriétaire de l'objet.
        return obj.user == request.user


class IsRegularUser(BasePermission):
    """
    Permission pour les utilisateurs ayant le rôle USER
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role == 'USER')


class IsArbitre(BasePermission):
    """
    Permission pour les arbitres
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role == 'ARBITRE')


class IsAdmin(BasePermission):
    """
    Permission pour les administrateurs
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role == 'ADMIN')


class IsAdminOrArbitre(BasePermission):
    """
    Permission pour les administrateurs et arbitres
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role in ['ADMIN', 'ARBITRE'])


class IsTransactionParticipant(BasePermission):
    """
    Permission pour les participants d'une transaction (buyer, seller)
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Si c'est une transaction escrow
        if hasattr(obj, 'buyer') and hasattr(obj, 'seller'):
            return request.user in [obj.buyer, obj.seller]
        
        # Si c'est un objet lié à une transaction
        if hasattr(obj, 'transaction'):
            return request.user in [obj.transaction.buyer, obj.transaction.seller]
        
        return False


class IsKYCVerified(BasePermission):
    """
    Permission pour les utilisateurs avec KYC vérifié
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.kyc_status == 'VERIFIED')


class CanCreateEscrow(BasePermission):
    """
    Permission pour créer une transaction escrow
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # L'utilisateur doit avoir un rôle USER et un KYC vérifié
        return (request.user.role == 'USER' and 
                request.user.kyc_status == 'VERIFIED')


class CanManageDispute(BasePermission):
    """
    Permission pour gérer les litiges
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.role in ['ADMIN', 'ARBITRE'])
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Admin peut tout faire
        if request.user.role == 'ADMIN':
            return True
        
        # Arbitre peut gérer les disputes qui lui sont assignées
        if request.user.role == 'ARBITRE':
            return obj.arbitre == request.user
        
        return False


class IsTransactionInCorrectState(BasePermission):
    """
    Permission basée sur l'état de la transaction
    """
    allowed_states = []  # À surcharger dans les vues
    
    def has_object_permission(self, request, view, obj):
        if hasattr(view, 'allowed_states'):
            allowed_states = view.allowed_states
        else:
            allowed_states = self.allowed_states
        
        if hasattr(obj, 'status'):
            return obj.status in allowed_states
        elif hasattr(obj, 'transaction') and hasattr(obj.transaction, 'status'):
            return obj.transaction.status in allowed_states
        
        return True  # Si pas d'état à vérifier, on autorise


class IsAdminOrReadOnly(BasePermission):
    """
    Permission pour permettre la lecture à tous et l'écriture aux admins seulement
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsArbitreOrReadOnly(BasePermission):
    """
    Permission pour permettre la lecture à tous et l'écriture aux arbitres et admins
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (request.user.is_authenticated and 
                request.user.role in ['ARBITRE', 'ADMIN'])
