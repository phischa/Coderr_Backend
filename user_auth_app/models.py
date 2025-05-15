from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    """
    Extension of the User model with additional profile information.
    Two types of profiles: business and customer.
    """
    USER_TYPES = {
        ('businuss', 'Business'),
        ('customer', 'Custome'),
    }
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    file = models.ImageField(upload_to='profile-images/', null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    tel = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    working_hours = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=USER_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_guest = models.BooleanField(default=False)

    @property
    def username(self):
        return self.user.username
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def email(self):
        return self.user.email
    
    def __str__(self):
        """
        String representation of the UserProfile.
        
        Returns:
            str: Username followed by user type (Business or Customer)
        """
        return f"{self.user.username} ({self.type})"