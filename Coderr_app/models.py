from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Offer(models.Model):
    """
    Service offers created by business users.
    Each offer has different tiers (basic, standard, premium).
    """
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='offer_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def min_price(self):
        """Returns the minimum price across all detail options"""
        details = self.details.all()
        if details:
            return min(detail.price for detail in details)
        return 0
    
    @property
    def min_delivery_time(self):
        """Returns the minimum delivery time across all detail options"""
        details = self.details.all()
        if details:
            return min(detail.delivery_time_in_days for detail in details)
        return 0
    
    @property
    def user(self):
        """Returns the creator's user ID for easy access in API responses"""
        return self.creator.id
    
    def __str__(self):
        return self.title


class OfferDetail(models.Model):
    """
    Different pricing tiers for each offer (basic, standard, premium).
    """
    OFFER_TYPES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]
    
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='details')
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPES)
    title = models.CharField(max_length=255)
    revisions = models.IntegerField(help_text="-1 for unlimited revisions")
    delivery_time_in_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['offer', 'offer_type']
    
    def __str__(self):
        return f"{self.offer.title} - {self.offer_type}"


class Feature(models.Model):
    """
    Features included in each offer detail.
    """
    offer_detail = models.ForeignKey(OfferDetail, on_delete=models.CASCADE, related_name='features')
    description = models.CharField(max_length=255)
    
    def __str__(self):
        return self.description


class Order(models.Model):
    """
    Customer orders for specific offer details.
    """
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_customer')
    business_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_business')
    offer_detail = models.ForeignKey(OfferDetail, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def features(self):
        """Returns the features from the offer detail"""
        return [feature.description for feature in self.offer_detail.features.all()]
    
    @property
    def title(self):
        """Returns the title from the offer detail"""
        return self.offer_detail.title
    
    @property
    def price(self):
        """Returns the price from the offer detail"""
        return self.offer_detail.price
    
    @property
    def delivery_time_in_days(self):
        """Returns the delivery time from the offer detail"""
        return self.offer_detail.delivery_time_in_days
    
    @property
    def revisions(self):
        """Returns the revisions from the offer detail"""
        return self.offer_detail.revisions
    
    @property
    def customer_user(self):
        """Returns the customer user ID for API compatibility"""
        return self.customer.id
    
    def __str__(self):
        return f"Order #{self.id} - {self.offer_detail.offer.title} ({self.status})"


class Review(models.Model):
    """
    Customer reviews for business users.
    """
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    business_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # One reviewer can only review a business user once
        unique_together = ['reviewer', 'business_user']
        # Default ordering by updated_at descending
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.business_user.username}"


class BaseInfo(models.Model):
    """
    General site statistics displayed on the index page.
    """
    total_users = models.IntegerField(default=0)
    total_offers = models.IntegerField(default=0)
    total_completed_orders = models.IntegerField(default=0)
    total_reviews = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Base Info"
        verbose_name_plural = "Base Info"
    
    def __str__(self):
        return "Site Statistics"
    
    @classmethod
    def get_or_create_singleton(cls):
        """Get the singleton instance or create if it doesn't exist"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    @classmethod
    def update_stats(cls):
        """Update the statistics from the database"""
        obj = cls.get_or_create_singleton()
        obj.total_users = User.objects.count()
        obj.total_offers = Offer.objects.count()
        obj.total_completed_orders = Order.objects.filter(status='completed').count()
        obj.total_reviews = Review.objects.count()
        obj.save()
        return obj
