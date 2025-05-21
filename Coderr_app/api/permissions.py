from rest_framework.permissions import BasePermission

class IsBusinessUser(BasePermission):
    """
    Custom permission to only allow business users to access a view.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                hasattr(request.user, 'profile') and 
                request.user.profile.type == 'business')

class IsCustomerUser(BasePermission):
    """
    Custom permission to only allow customer users to access a view.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                hasattr(request.user, 'profile') and 
                request.user.profile.type == 'customer')