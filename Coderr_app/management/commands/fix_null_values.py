from django.core.management.base import BaseCommand
from Coderr_app.models import OfferDetail, Offer, Order
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Fix NULL values in OfferDetail and related models'

    def handle(self, *args, **options):
        """Fix all NULL values in OfferDetail and related models"""
        
        # Count existing null values in OfferDetail
        null_revisions = OfferDetail.objects.filter(revisions__isnull=True).count()
        null_delivery = OfferDetail.objects.filter(delivery_time_in_days__isnull=True).count()
        null_price = OfferDetail.objects.filter(price__isnull=True).count()
        null_title = OfferDetail.objects.filter(title__isnull=True).count()
        null_offer_type = OfferDetail.objects.filter(offer_type__isnull=True).count()
        
        # Count null values in Offer
        null_offer_title = Offer.objects.filter(title__isnull=True).count()
        null_offer_description = Offer.objects.filter(description__isnull=True).count()
        
        self.stdout.write(f'Found NULL values in OfferDetail:')
        self.stdout.write(f'  - revisions: {null_revisions}')
        self.stdout.write(f'  - delivery_time_in_days: {null_delivery}')
        self.stdout.write(f'  - price: {null_price}')
        self.stdout.write(f'  - title: {null_title}')
        self.stdout.write(f'  - offer_type: {null_offer_type}')
        
        self.stdout.write(f'Found NULL values in Offer:')
        self.stdout.write(f'  - title: {null_offer_title}')
        self.stdout.write(f'  - description: {null_offer_description}')
        
        # Fix NULL values in OfferDetail
        fixed_count = 0
        
        # Fix revisions (default to 1)
        result = OfferDetail.objects.filter(revisions__isnull=True).update(revisions=1)
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL revisions → 1')
        
        # Fix delivery_time_in_days (default to 1)
        result = OfferDetail.objects.filter(delivery_time_in_days__isnull=True).update(delivery_time_in_days=1)
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL delivery_time_in_days → 1')
        
        # Fix price (default to 0.0)
        result = OfferDetail.objects.filter(price__isnull=True).update(price=0.0)
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL price → 0.0')
        
        # Fix title (default to empty string)
        result = OfferDetail.objects.filter(title__isnull=True).update(title='')
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL title → ""')
        
        # Fix offer_type (default to 'basic')
        result = OfferDetail.objects.filter(offer_type__isnull=True).update(offer_type='basic')
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL offer_type → "basic"')
        
        # Fix NULL values in Offer
        # Fix offer title
        result = Offer.objects.filter(title__isnull=True).update(title='')
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL offer title → ""')
        
        # Fix offer description
        result = Offer.objects.filter(description__isnull=True).update(description='')
        fixed_count += result
        self.stdout.write(f'Fixed {result} NULL offer description → ""')
        
        # Also fix any potential zero or negative values that should have minimums
        # Fix revisions that are 0 (should be at least 1 or -1 for unlimited)
        zero_revisions = OfferDetail.objects.filter(revisions=0).update(revisions=1)
        if zero_revisions > 0:
            self.stdout.write(f'Fixed {zero_revisions} zero revisions → 1')
            fixed_count += zero_revisions
        
        # Fix delivery_time_in_days that are 0 or negative
        invalid_delivery = OfferDetail.objects.filter(delivery_time_in_days__lte=0).update(delivery_time_in_days=1)
        if invalid_delivery > 0:
            self.stdout.write(f'Fixed {invalid_delivery} invalid delivery_time_in_days → 1')
            fixed_count += invalid_delivery
        
        # Fix negative prices
        negative_prices = OfferDetail.objects.filter(price__lt=0).update(price=0.0)
        if negative_prices > 0:
            self.stdout.write(f'Fixed {negative_prices} negative prices → 0.0')
            fixed_count += negative_prices
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {fixed_count} NULL/invalid values!')
        )