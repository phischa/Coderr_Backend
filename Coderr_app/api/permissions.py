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