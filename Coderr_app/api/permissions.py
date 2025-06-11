from rest_framework.permissions import BasePermission
from user_auth_app.models import Profile


class IsBusinessUser(BasePermission):
    """
    Custom permission to only allow business users to access a view.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            return request.user.profile.type == 'business'
        except Profile.DoesNotExist:
            return False


class IsCustomerUser(BasePermission):
    """
    Custom permission to only allow customer users to access a view.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            return request.user.profile.type == 'customer'
        except Profile.DoesNotExist:
            return False

class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission for offers:
    - List: No authentication required  
    - Retrieve: Authentication required
    - Create: Business user required (handled separately)
    - Update/Delete: Owner only
    """
    def has_permission(self, request, view):
        if view.action == 'list':
            return True  # GET /api/offers/ - no auth required
        elif view.action == 'retrieve':
            return request.user.is_authenticated  # GET /api/offers/{id}/ - auth required
        elif view.action == 'create':
            return request.user.is_authenticated  # Business check done in view
        elif view.action in ['update', 'partial_update', 'destroy']:
            return request.user.is_authenticated
        return False
    
    def has_object_permission(self, request, view, obj):
        # For update/delete operations, check ownership
        if view.action in ['update', 'partial_update', 'destroy']:
            return obj.creator == request.user
        return True