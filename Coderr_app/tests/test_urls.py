from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from rest_framework.test import APIClient


class URLPatternsTest(TestCase):
    """Test URL pattern resolution"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='test123'
        )
        self.client = APIClient()
    
    def test_offer_urls(self):
        """Test offer-related URLs"""
        # Test list URL
        url = reverse('offer-list')
        self.assertEqual(url, '/api/offers/')
        
        # Test detail URL
        url = reverse('offer-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/api/offers/1/')
        
        # Test URL resolution
        resolver = resolve('/api/offers/')
        self.assertEqual(resolver.view_name, 'offer-list')
    
    def test_order_urls(self):
        """Test order-related URLs"""
        # Test list URL
        url = reverse('order-list')
        self.assertEqual(url, '/api/orders/')
        
        # Test custom action URLs
        url = reverse('order-count', kwargs={'user_id': 1})
        self.assertIn('order-count', url)
        
        url = reverse('completed-order-count', kwargs={'user_id': 1})
        self.assertIn('completed-order-count', url)
    
    def test_review_urls(self):
        """Test review-related URLs"""
        # Test list URL
        url = reverse('review-list')
        self.assertEqual(url, '/api/reviews/')
        
        # Test custom action URLs
        url = reverse('business-reviews', kwargs={'business_user_id': 1})
        self.assertIn('business', url)
        
        url = reverse('reviewer-reviews', kwargs={'reviewer_id': 1})
        self.assertIn('reviewer', url)
    
    def test_profile_urls(self):
        """Test profile-related URLs"""
        # Test list URL
        url = reverse('profile-list')
        self.assertEqual(url, '/api/profiles/')
        
        # Test custom action URLs
        url = reverse('business-profiles-list')
        self.assertIn('business', url)
        
        url = reverse('customer-profiles-list')
        self.assertIn('customer', url)
        
        url = reverse('profile-by-user', kwargs={'pk': 1})
        self.assertIn('user', url)
    
    def test_base_info_url(self):
        """Test base info URL"""
        url = reverse('base-info')
        self.assertEqual(url, '/api/base-info/')
        
        # Test URL resolution
        resolver = resolve('/api/base-info/')
        self.assertEqual(resolver.view_name, 'base-info')
        