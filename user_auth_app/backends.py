from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authentication backend that allows users to log in with either email or username.
    
    Extends Django's default ModelBackend to support authentication with
    both username and email address using the same login field.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user based on either username or email address.
        
        Attempts to find a user with the provided credential matching either 
        their username or email (case-insensitive), then verifies the password.
        
        Args:
            request: The HTTP request (may be None)
            username: The credential provided (could be username or email)
            password: The password to verify
            **kwargs: Additional keyword arguments
            
        Returns:
            User: The authenticated user instance if successful, or None if authentication fails
        """
        UserModel = get_user_model()
        
        # Try to find the user by username or email
        try:
            # Use Q objects for OR query (username OR email)
            user = UserModel.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).first()
            
            # Check password if a user was found
            if user and user.check_password(password):
                return user
                
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce timing attacks
            UserModel().set_password(password)
            
        return None