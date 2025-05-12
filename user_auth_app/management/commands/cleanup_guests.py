from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user_auth_app.models import UserProfile
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    """
    Django management command for cleaning up old guest accounts.
    
    This command removes guest user accounts that were created more than
    7 days ago to prevent the database from accumulating unused accounts.
    Guest accounts are identified by the 'is_guest' flag in their UserProfile.
    """
    help = 'Cleans up old guest accounts'

    def handle(self, *args, **options):
        """
        Execute the command to clean up old guest accounts.
        
        Identifies guest accounts created more than 7 days ago and deletes them,
        along with their associated User objects. Due to the CASCADE relationship,
        deleting the User also removes the associated UserProfile.
        
        Args:
            *args: Additional positional arguments.
            **options: Additional keyword arguments provided by the management command.
            
        Returns:
            None: Outputs results to stdout.
        """
        cutoff_date = timezone.now() - timedelta(days=7)
        old_guests = UserProfile.objects.filter(
            is_guest=True, 
            created_at__lt=cutoff_date
        )
        
        for profile in old_guests:
            user = profile.user
            self.stdout.write(f"Deleting guest: {user.username}")
            user.delete()  # Also deletes the profile due to CASCADE
        
        self.stdout.write(f"Cleanup completed. {old_guests.count()} guest accounts were deleted.")