from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    """
    Extension of the User model with additional profile information.
    Two types of profiles: business and customer.
    
    This is the central profile model that stores all user-related information
    beyond the basic User model fields.
    """
    USER_TYPES = [  
        ('business', 'Business'), 
        ('customer', 'Customer'), 
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    file = models.ImageField(upload_to='profile-images/', null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    tel = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    working_hours = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=USER_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_guest = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

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

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to create a Profile whenever a User is created.
    
    Args:
        sender: The model class that sent the signal (User)
        instance: The actual User instance being saved
        created: Boolean indicating if this is a new record
    """
    if created:
        # Default to customer type for new profiles
        Profile.objects.create(user=instance, type='customer')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler to save a Profile whenever a User is saved.
    
    Args:
        sender: The model class that sent the signal (User)
        instance: The actual User instance being saved
    """
    instance.profile.save()