from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """
    Extended user profile model that adds additional fields to Django's User model.
    
    This model maintains a one-to-one relationship with Django's built-in User model
    and adds custom fields for tracking guest status and creation time.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_guest = models.BooleanField(default=False)  # New field added
    created_at = models.DateTimeField(auto_now_add=True)  # Optional: for later cleanup
    
    def __str__(self):
        """
        String representation of the UserProfile.
        
        Returns:
            str: Username followed by status (Guest or User)
        """
        return f"{self.user.username} ({'Guest' if self.is_guest else 'User'})"