from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from decimal import Decimal
from user_auth_app.models import Profile
from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo
from Coderr_app.api.serializers import (
    UserSerializer, ProfileSerializer, ProfileUpdateSerializer,
    OfferSerializer, OfferWithDetailsSerializer, OfferDetailSerializer,
    OrderSerializer, ReviewSerializer, BaseInfoSerializer
)


class UserSerializerTest(TestCase):
    """Test UserSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_serialization(self):
        """Test basic user serialization"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['id'], self.user.id)
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['email'], 'test@test.com')


class ProfileSerializerTest(TestCase):
    """Test ProfileSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        # Profile is auto-created, just update it with additional data
        self.user.profile.type = 'business'
        self.user.profile.location = 'Test City'
        self.user.profile.tel = '123-456-7890'
        self.user.profile.description = 'Test business profile'
        self.user.profile.working_hours = '9 AM - 5 PM'
        self.user.profile.save()
    
    def test_profile_serialization(self):
        """Test profile serialization with user data"""
        serializer = ProfileSerializer(self.user.profile)
        data = serializer.data
        
        # Test Profile fields
        self.assertEqual(data['id'], self.user.profile.id)
        self.assertEqual(data['user'], self.user.id)
        self.assertEqual(data['type'], 'business')
        self.assertEqual(data['location'], 'Test City')
        self.assertEqual(data['tel'], '123-456-7890')
        self.assertEqual(data['description'], 'Test business profile')
        self.assertEqual(data['working_hours'], '9 AM - 5 PM')
        
        # Test User properties
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['email'], 'test@test.com')
        self.assertEqual(data['is_guest'], False)


class ProfileUpdateSerializerTest(TestCase):
    """Test ProfileUpdateSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='old@test.com',
            password='testpass123',
            first_name='Old',
            last_name='Name'
        )
        # Profile is auto-created, just update the type
        self.user.profile.type = 'business'
        self.user.profile.location = 'Old City'
        self.user.profile.save()
    
    def test_profile_update_with_user_fields(self):
        """Test updating profile and user fields together"""
        data = {
            'location': 'New City',
            'tel': '555-1234',
            'description': 'Updated description',
            'first_name': 'New',
            'last_name': 'Name',
            'email': 'new@test.com'
        }
        
        serializer = ProfileUpdateSerializer(self.user.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_profile = serializer.save()
        
        # Refresh user from database
        self.user.refresh_from_db()
        
        # Test Profile fields were updated
        self.assertEqual(updated_profile.location, 'New City')
        self.assertEqual(updated_profile.tel, '555-1234')
        self.assertEqual(updated_profile.description, 'Updated description')
        
        # Test User fields were updated
        self.assertEqual(self.user.first_name, 'New')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'new@test.com')


class OfferSerializerTest(TestCase):
    """Test OfferSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', change to 'business'
        self.user.profile.type = 'business'
        self.user.profile.save()
        
        self.offer = Offer.objects.create(
            creator=self.user,
            title='Test Service',
            description='Test service description'
        )
        
        # Create offer details for min_price and min_delivery_time properties
        self.basic_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        self.premium_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='premium',
            title='Premium Package',
            revisions=5,
            delivery_time_in_days=3,
            price=Decimal('300.00')
        )
    
    def test_offer_serialization(self):
        """Test offer serialization"""
        serializer = OfferSerializer(self.offer)
        data = serializer.data
        
        self.assertEqual(data['id'], self.offer.id)
        self.assertEqual(data['title'], 'Test Service')
        self.assertEqual(data['description'], 'Test service description')
        self.assertEqual(data['user'], self.user.id)
        self.assertEqual(data['min_price'], Decimal('100.00'))
        self.assertEqual(data['min_delivery_time'], 3)
        
        # Test details structure
        self.assertIn('details', data)
        self.assertEqual(len(data['details']), 2)
        
        # Check that details contain offer_type field (this was missing and causing failure)
        for detail in data['details']:
            self.assertIn('id', detail)
            self.assertIn('offer_type', detail)  # This field must be present now
            self.assertIn('url', detail)
        
        # Check specific offer types are present
        detail_types = [detail['offer_type'] for detail in data['details']]
        self.assertIn('basic', detail_types)
        self.assertIn('premium', detail_types)


class OfferWithDetailsSerializerTest(TestCase):
    """Test OfferWithDetailsSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', change to 'business'
        self.user.profile.type = 'business'
        self.user.profile.save()
        
        self.offer = Offer.objects.create(
            creator=self.user,
            title='Test Service',
            description='Test service description'
        )
        
        # Create offer detail with features
        self.offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        # Add features
        Feature.objects.create(offer_detail=self.offer_detail, description='Feature 1')
        Feature.objects.create(offer_detail=self.offer_detail, description='Feature 2')
    
    def test_offer_with_details_serialization(self):
        """Test offer serialization with expanded details"""
        serializer = OfferWithDetailsSerializer(self.offer)
        data = serializer.data
        
        self.assertEqual(data['id'], self.offer.id)
        self.assertEqual(data['title'], 'Test Service')
        self.assertEqual(data['user'], self.user.id)
        
        # Test expanded details
        self.assertIn('details', data)
        self.assertEqual(len(data['details']), 1)
        
        detail = data['details'][0]
        self.assertEqual(detail['offer_type'], 'basic')
        self.assertEqual(detail['title'], 'Basic Package')
        self.assertEqual(detail['revisions'], 2)
        self.assertEqual(detail['delivery_time_in_days'], 7)
        self.assertEqual(detail['price'], '100.00')  # Model DecimalField returns string
        
        # Test features
        self.assertIn('features', detail)
        self.assertEqual(len(detail['features']), 2)
        self.assertIn('Feature 1', detail['features'])
        self.assertIn('Feature 2', detail['features'])


class OfferDetailSerializerTest(TestCase):
    """Test OfferDetailSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', change to 'business'
        self.user.profile.type = 'business'
        self.user.profile.save()
        
        self.offer = Offer.objects.create(
            creator=self.user,
            title='Test Service',
            description='Test service description'
        )
        
        self.offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        # Add features
        Feature.objects.create(offer_detail=self.offer_detail, description='Feature 1')
        Feature.objects.create(offer_detail=self.offer_detail, description='Feature 2')
    
    def test_offer_detail_serialization(self):
        """Test offer detail serialization"""
        serializer = OfferDetailSerializer(self.offer_detail)
        data = serializer.data
        
        self.assertEqual(data['id'], self.offer_detail.id)
        self.assertEqual(data['offer'], self.offer.id)
        self.assertEqual(data['offer_type'], 'basic')
        self.assertEqual(data['title'], 'Basic Package')
        self.assertEqual(data['revisions'], 2)
        self.assertEqual(data['delivery_time_in_days'], 7)
        self.assertEqual(data['price'], '100.00')  # Model DecimalField returns string
        
        # Test features serialization
        self.assertIn('features', data)
        self.assertEqual(len(data['features']), 2)
        self.assertIn('Feature 1', data['features'])
        self.assertIn('Feature 2', data['features'])


class OrderSerializerTest(TestCase):
    """Test OrderSerializer"""
    
    def setUp(self):
        """Set up test data"""
        # Create business user
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', change to 'business'
        self.business_user.profile.type = 'business'
        self.business_user.profile.save()
        
        # Create customer user
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', keep it as is
        
        # Create offer and offer detail
        self.offer = Offer.objects.create(
            creator=self.business_user,
            title='Test Service',
            description='Test service description'
        )
        
        self.offer_detail = OfferDetail.objects.create(
            offer=self.offer,
            offer_type='basic',
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=7,
            price=Decimal('100.00')
        )
        
        # Add features
        Feature.objects.create(offer_detail=self.offer_detail, description='Feature 1')
        Feature.objects.create(offer_detail=self.offer_detail, description='Feature 2')
        
        # Create order
        self.order = Order.objects.create(
            customer=self.customer_user,
            business_user=self.business_user,
            offer_detail=self.offer_detail,
            status='in_progress'
        )
    
    def test_order_serialization(self):
        """Test order serialization"""
        serializer = OrderSerializer(self.order)
        data = serializer.data
        
        self.assertEqual(data['id'], self.order.id)
        self.assertEqual(data['customer'], self.customer_user.id)
        self.assertEqual(data['business_user'], self.business_user.id)
        self.assertEqual(data['customer_username'], 'customer')
        self.assertEqual(data['business_username'], 'businessuser')
        self.assertEqual(data['offer_detail'], self.offer_detail.id)
        self.assertEqual(data['status'], 'in_progress')
        
        # Test properties from offer_detail
        self.assertEqual(data['title'], 'Basic Package')
        self.assertEqual(data['delivery_time_in_days'], 7)
        self.assertEqual(data['revisions'], 2)
        self.assertEqual(data['price'], Decimal('100.00'))
        self.assertEqual(data['customer_user'], self.customer_user.id)
        
        # Test features
        self.assertIn('features', data)
        self.assertEqual(len(data['features']), 2)
        self.assertIn('Feature 1', data['features'])
        self.assertIn('Feature 2', data['features'])


class ReviewSerializerTest(TestCase):
    """Test ReviewSerializer"""
    
    def setUp(self):
        """Set up test data"""
        # Create business user
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', change to 'business'
        self.business_user.profile.type = 'business'
        self.business_user.profile.save()
        
        # Create customer user
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Profile is auto-created as 'customer', keep it as is
        
        # Create review
        self.review = Review.objects.create(
            reviewer=self.customer_user,
            business_user=self.business_user,
            rating=5,
            description='Excellent service!'
        )
    
    def test_review_serialization(self):
        """Test review serialization"""
        serializer = ReviewSerializer(self.review)
        data = serializer.data
        
        self.assertEqual(data['id'], self.review.id)
        self.assertEqual(data['reviewer'], self.customer_user.id)
        self.assertEqual(data['business_user'], self.business_user.id)
        self.assertEqual(data['reviewer_username'], 'customer')
        self.assertEqual(data['business_user_username'], 'businessuser')
        self.assertEqual(data['rating'], 5)
        self.assertEqual(data['description'], 'Excellent service!')


class BaseInfoSerializerTest(TestCase):
    """Test BaseInfoSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.base_info = BaseInfo.objects.create(
            total_users=100,
            total_offers=50,
            total_completed_orders=25,
            total_reviews=75
        )
    
    def test_base_info_serialization(self):
        """Test base info serialization"""
        serializer = BaseInfoSerializer(self.base_info)
        data = serializer.data
        
        self.assertEqual(data['total_users'], 100)
        self.assertEqual(data['total_offers'], 50)
        self.assertEqual(data['total_completed_orders'], 25)
        self.assertEqual(data['total_reviews'], 75)


class SerializerLine217Test(TestCase):
    """Test exact line 217 in serializers.py"""
    
    def test_serializer_line_217_validation_error(self):
        """Test the exact validation error on line 217"""
        business_user = User.objects.create_user(
            username='business',
            email='business@test.com',
            password='test123'
        )
        business_user.profile.type = 'business'
        business_user.profile.save()
        
        customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='test123'
        )
        
        serializer = OrderSerializer(data={
            'offer_detail_id': 99999,  # Non-existent
            'customer': customer_user.id,
            'business_user': business_user.id
        })
        
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        self.assertIn('offer_detail_id', serializer.errors)
