from rest_framework import permissions


class IsProfileOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a profile to edit it.
    
    This permission class ensures that:
    - Any authenticated user can view profiles (GET requests)
    - Only the owner of a profile can update it (PATCH/PUT requests)
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions are only allowed to the owner of the profile
        return obj.user == request.user