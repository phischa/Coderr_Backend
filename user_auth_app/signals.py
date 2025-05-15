from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a Profile when a User is created.
    
    This function is connected to Django's post_save signal for the User model
    and will create a corresponding Profile instance for newly created users.
    
    Args:
        sender: The model class that sent the signal (User)
        instance: The actual User instance that was saved
        created: Boolean flag indicating if this is a new record
        **kwargs: Additional keyword arguments from the signal
    """
    if created:
        Profile.objects.create(
            user=instance, 
            type='customer' 
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler to save the Profile when a User is saved.
    
    This function is connected to Django's post_save signal for the User model
    and ensures the associated Profile is updated whenever a User is saved.
    If no profile exists, it creates one to maintain data integrity.
    
    Args:
        sender: The model class that sent the signal (User)
        instance: The actual User instance that was saved
        **kwargs: Additional keyword arguments from the signal
    """
    try:
        instance.profile.save()
    except User.profile.RelatedObjectDoesNotExist:
        Profile.objects.create(
            user=instance,
            type='customer'
        )