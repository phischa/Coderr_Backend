from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from user_auth_app.models import Profile
from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo


class OfferModelTest(TestCase):
    """Test Offer model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.user).delete()
        self.profile = Profile.objects.create(
            user=self.user,
            type='business',
            location='Test City'
        )
            
        self.offer = Offer.objects.create(
            creator=self.user,
            title='Test Web Development Service',
            description='Professional web development services'
        )
    
    def test_offer_creation(self):
        """Test basic offer creation"""
        self.assertEqual(self.offer.title, 'Test Web Development Service')
        self.assertEqual(self.offer.creator, self.user)
        self.assertEqual(str(self.offer), 'Test Web Development Service')
    
    def test_offer_properties(self):
        """Test Offer model properties"""
        # Create offer details to test properties
        basic_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        premium_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='premium',
            title='Premium Package',
            revisions=5,
            delivery_time_in_days=3,
            price=Decimal('300.00')
        )
        
        # Test min_price property
        self.assertEqual(self.offer.min_price, Decimal('100.00'))
        
        # Test min_delivery_time property
        self.assertEqual(self.offer.min_delivery_time, 3)
        
        # Test user property
        self.assertEqual(self.offer.user, self.user.id)
    
    def test_offer_missing_creator(self):
        """Test that missing creator raises error"""
        with self.assertRaises(IntegrityError):
            Offer.objects.create(
                title='Test Service',
                description='Test description'
            )
    
    def test_offer_empty_title(self):
        """Test that empty title raises ValidationError on full_clean()"""
        # CharField with blank=False (default) doesn't allow empty strings during validation
        offer = Offer(
            creator=self.user,
            title='',  # Empty string
            description='Test description'
        )
        with self.assertRaises(ValidationError):
            offer.full_clean()
    
    def test_offer_required_fields_validation(self):
        """Test validation using full_clean()"""
        # Test with valid title - should work
        offer = Offer(
            creator=self.user,
            title='Valid Title',
            description='Test description'
        )
        # This should not raise an error
        offer.full_clean()
        
        # Test with no creator - this should raise ValidationError
        offer_no_creator = Offer(
            title='Test',
            description='Test description'
        )
        with self.assertRaises(ValidationError):
            offer_no_creator.full_clean()


class OfferDetailModelTest(TestCase):
    """Test OfferDetail model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.user).delete()
        self.profile = Profile.objects.create(
            user=self.user,
            type='business'
        )
            
        self.offer = Offer.objects.create(
            creator=self.user,
            title='Test Service',
            description='Test description'
        )
    
    def test_offer_detail_creation(self):
        """Test basic offer detail creation"""
        offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        self.assertEqual(offer_detail.offer, self.offer)
        self.assertEqual(offer_detail.offer_type, 'basic')
        self.assertEqual(offer_detail.price, Decimal('100.00'))
    
    def test_offer_detail_str(self):
        """Test string representation"""
        offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        # The actual __str__ method returns "offer_title - offer_type"
        expected_str = f"{self.offer.title} - {offer_detail.offer_type}"
        self.assertEqual(str(offer_detail), expected_str)
    
    def test_offer_detail_types(self):
        """Test different offer detail types"""
        types = ['basic', 'standard', 'premium']
        
        for offer_type in types:
            offer_detail = OfferDetail.objects.create(
                offer=self.offer,
                offer_type=offer_type,
                title=f'{offer_type.title()} Package',
                revisions=2,
                delivery_time_in_days=7,
                price=Decimal('100.00')
            )
            self.assertEqual(offer_detail.offer_type, offer_type)
    
    def test_offer_detail_deletion_with_offer(self):
        """Test that offer details are deleted when offer is deleted"""
        offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        offer_detail_id = offer_detail.id
        self.offer.delete()
        
        # OfferDetail should be deleted due to CASCADE
        with self.assertRaises(OfferDetail.DoesNotExist):
            OfferDetail.objects.get(id=offer_detail_id)


class OrderModelTest(TestCase):
    """Test Order model"""
    
    def setUp(self):
        """Set up test data"""
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.business_user).delete()
        self.business_profile = Profile.objects.create(
            user=self.business_user,
            type='business'
        )
        
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.customer_user).delete()
        self.customer_profile = Profile.objects.create(
            user=self.customer_user,
            type='customer'
        )
        
        self.offer = Offer.objects.create(
            creator=self.business_user,
            title='Test Service',
            description='Test description'
        )
        
        self.offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        Feature.objects.create(
            offer_detail=self.offer_detail,
            description='Feature 1'
        )
        Feature.objects.create(
            offer_detail=self.offer_detail,
            description='Feature 2'
        )
    
    def test_order_creation(self):
        """Test basic order creation"""
        order = Order.objects.create(
            customer=self.customer_user,
            business_user=self.business_user,
            offer_detail=self.offer_detail
        )
        
        self.assertEqual(order.customer, self.customer_user)
        self.assertEqual(order.business_user, self.business_user)
        self.assertEqual(order.offer_detail, self.offer_detail)
        self.assertEqual(order.status, 'in_progress')  # Default status
    
    def test_order_status_choices(self):
        """Test different order statuses"""
        order = Order.objects.create(
            customer=self.customer_user,
            business_user=self.business_user,
            offer_detail=self.offer_detail
        )
        
        # Test different statuses
        statuses = ['in_progress', 'completed', 'cancelled']
        
        for status in statuses:
            order.status = status
            order.save()
            order.refresh_from_db()
            self.assertEqual(order.status, status)
    
    def test_order_relationships(self):
        """Test that order relationships work correctly"""
        order = Order.objects.create(
            customer=self.customer_user,
            business_user=self.business_user,
            offer_detail=self.offer_detail
        )
        
        # Test that profiles are accessible through relationships
        self.assertEqual(order.customer.profile.type, 'customer')
        self.assertEqual(order.business_user.profile.type, 'business')


class ReviewModelTest(TestCase):
    """Test Review model"""
    
    def setUp(self):
        """Set up test data"""
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.business_user).delete()
        self.business_profile = Profile.objects.create(
            user=self.business_user,
            type='business'
        )
        
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.customer_user).delete()
        self.customer_profile = Profile.objects.create(
            user=self.customer_user,
            type='customer'
        )
    
    def test_review_creation(self):
        """Test basic review creation"""
        review = Review.objects.create(
            reviewer=self.customer_user,
            business_user=self.business_user,
            rating=5,
            description='Excellent service!'
        )
        
        self.assertEqual(review.reviewer, self.customer_user)
        self.assertEqual(review.business_user, self.business_user)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.description, 'Excellent service!')
    
    def test_review_rating_range(self):
        """Test that ratings are within valid range"""
        # Valid ratings should work - but we need different business users 
        # due to UNIQUE constraint on (reviewer_id, business_user_id)
        
        for i, rating in enumerate([1, 2, 3, 4, 5]):
            # Create a new business user for each review to avoid unique constraint
            business_user = User.objects.create_user(
                username=f'business_user_{i}',
                email=f'business_{i}@test.com',
                password='testpass123'
            )
            Profile.objects.filter(user=business_user).delete()
            Profile.objects.create(user=business_user, type='business')
            
            review = Review.objects.create(
                reviewer=self.customer_user,
                business_user=business_user,
                rating=rating,
                description=f'Rating {rating} review'
            )
            self.assertEqual(review.rating, rating)
    
    def test_review_relationships(self):
        """Test review relationships"""
        review = Review.objects.create(
            reviewer=self.customer_user,
            business_user=self.business_user,
            rating=4,
            description='Good service'
        )
        
        # Test that profiles are accessible
        self.assertEqual(review.reviewer.profile.type, 'customer')
        self.assertEqual(review.business_user.profile.type, 'business')


class FeatureModelTest(TestCase):
    """Test Feature model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        # Delete auto-created profile and create new one with correct values
        Profile.objects.filter(user=self.user).delete()
        self.profile = Profile.objects.create(
            user=self.user,
            type='business'
        )
        
        self.offer = Offer.objects.create(
            creator=self.user,
            title='Test Service',
            description='Test description'
        )
        
        self.offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
    
    def test_feature_creation(self):
        """Test basic feature creation"""
        feature = Feature.objects.create(
            offer_detail=self.offer_detail,
            description='Test feature'
        )
        
        self.assertEqual(feature.offer_detail, self.offer_detail)
        self.assertEqual(feature.description, 'Test feature')
        self.assertEqual(str(feature), 'Test feature')
    
    def test_feature_offer_detail_relationship(self):
        """Test that feature is properly linked to offer detail"""
        feature1 = Feature.objects.create(
            offer_detail=self.offer_detail,
            description='Feature 1'
        )
        feature2 = Feature.objects.create(
            offer_detail=self.offer_detail,
            description='Feature 2'
        )
        
        features = self.offer_detail.features.all()
        self.assertEqual(features.count(), 2)
        self.assertIn(feature1, features)
        self.assertIn(feature2, features)
    
    def test_feature_deletion_with_offer_detail(self):
        """Test that features are deleted when offer detail is deleted"""
        feature = Feature.objects.create(
            offer_detail=self.offer_detail,
            description='Test feature'
        )
        
        feature_id = feature.id
        self.offer_detail.delete()
        
        # Feature should be deleted due to CASCADE
        with self.assertRaises(Feature.DoesNotExist):
            Feature.objects.get(id=feature_id)


class BaseInfoModelTest(TestCase):
    """Test BaseInfo model"""
    
    def test_base_info_creation(self):
        """Test basic base info creation"""
        base_info = BaseInfo.objects.create(
            total_users=100,
            total_offers=50,
            total_completed_orders=25,
            total_reviews=75
        )
        
        self.assertEqual(base_info.total_users, 100)
        self.assertEqual(base_info.total_offers, 50)
        self.assertEqual(base_info.total_completed_orders, 25)
        self.assertEqual(base_info.total_reviews, 75)
        self.assertEqual(str(base_info), 'Site Statistics')
    
    def test_base_info_singleton(self):
        """Test BaseInfo singleton functionality"""
        # Test get_or_create_singleton
        base_info1 = BaseInfo.get_or_create_singleton()
        base_info2 = BaseInfo.get_or_create_singleton()
        
        # Should be the same instance
        self.assertEqual(base_info1.id, base_info2.id)
        self.assertEqual(base_info1.pk, 1)  # Should always have pk=1
    
    def test_base_info_update_stats(self):
        """Test BaseInfo update_stats method"""
        # Create some test data
        user = User.objects.create_user(username='testuser', password='test123')
        
        # Update stats
        base_info = BaseInfo.update_stats()
        
        # Should have updated user count
        self.assertGreaterEqual(base_info.total_users, 1)
        