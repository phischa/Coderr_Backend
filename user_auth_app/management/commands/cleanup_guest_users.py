from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from user_auth_app.models import Profile


class Command(BaseCommand):
    help = 'Clean up guest users older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete guest users older than this many days (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find guest users older than the cutoff date
        old_guest_users = User.objects.filter(
            profile__is_guest=True,
            date_joined__lt=cutoff_date
        )
        
        count = old_guest_users.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No guest users to clean up.'))
            return
        
        self.stdout.write(f'Found {count} guest users older than {days} days.')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No users will be deleted.'))
            for user in old_guest_users[:10]:  # Show first 10 users
                self.stdout.write(f'  - {user.username} (created: {user.date_joined})')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            # Delete the users (this will cascade delete profiles, orders, etc.)
            deleted_count, details = old_guest_users.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} guest users and related objects.'
                )
            )
            
            # Show details of what was deleted
            for model, count in details.items():
                if count > 0:
                    self.stdout.write(f'  - {model}: {count}')