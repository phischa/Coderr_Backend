# test_urls.py - Korrigierte URL Tests für Coderr_app
from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from rest_framework.test import APIClient


class URLPatternsTest(TestCase):
    """Test URL pattern resolution für Coderr_app spezifische URLs"""
    
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
        
        # Test detail resolution
        resolver = resolve('/api/offers/1/')
        self.assertEqual(resolver.view_name, 'offer-detail')
    
    def test_offer_detail_urls(self):
        """Test offer detail URLs"""
        # Test list URL
        url = reverse('offer-detail-list')
        self.assertEqual(url, '/api/offerdetails/')
        
        # Test detail URL
        url = reverse('offer-detail-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/api/offerdetails/1/')
        
        # Test URL resolution
        resolver = resolve('/api/offerdetails/')
        self.assertEqual(resolver.view_name, 'offer-detail-list')
    
    def test_order_urls(self):
        """Test order-related URLs"""
        # Test list URL
        url = reverse('order-list')
        self.assertEqual(url, '/api/orders/')
        
        # Test detail URL
        url = reverse('order-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/api/orders/1/')
        
        # Test custom action URLs
        url = reverse('order-count', kwargs={'user_id': 1})
        self.assertIn('order-count', url)
        
        url = reverse('completed-order-count', kwargs={'user_id': 1})
        self.assertIn('completed-order-count', url)
        
        # Test URL resolution
        resolver = resolve('/api/orders/')
        self.assertEqual(resolver.view_name, 'order-list')
    
    def test_review_urls(self):
        """Test review-related URLs"""
        # Test list URL
        url = reverse('review-list')
        self.assertEqual(url, '/api/reviews/')
        
        # Test detail URL
        url = reverse('review-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/api/reviews/1/')
        
        # Test custom action URLs
        url = reverse('business-reviews', kwargs={'business_user_id': 1})
        self.assertIn('business', url)
        self.assertIn('1', url)
        
        url = reverse('reviewer-reviews', kwargs={'reviewer_id': 1})
        self.assertIn('reviewer', url)
        self.assertIn('1', url)
        
        # Test URL resolution
        resolver = resolve('/api/reviews/')
        self.assertEqual(resolver.view_name, 'review-list')
    
    def test_profile_urls(self):
        """Test profile-related URLs (diese sind in Coderr_app, nicht user_auth_app)"""
        # Teste nur die Profile-URLs die tatsächlich in Coderr_app definiert sind
        # Basierend auf der urls.py sind das:
        
        # Test profile detail URL
        url = reverse('profile-detail', kwargs={'pk': 1})
        self.assertIn('profile', url)
        self.assertIn('1', url)
        
        # Test profile by user URL
        url = reverse('profile-by-user', kwargs={'pk': 1})
        self.assertIn('profile', url)
        self.assertIn('user', url)
        self.assertIn('1', url)
        
        # Test business profiles URL
        url = reverse('business-profiles-list')
        self.assertIn('profiles', url)
        self.assertIn('business', url)
        
        # Test customer profiles URL
        url = reverse('customer-profiles-list')
        self.assertIn('profiles', url)
        self.assertIn('customer', url)
    
    def test_base_info_url(self):
        """Test base info URL"""
        url = reverse('base-info')
        self.assertEqual(url, '/api/base-info/')
        
        # Test URL resolution
        resolver = resolve('/api/base-info/')
        self.assertEqual(resolver.view_name, 'base-info')
    
    def test_url_resolution_consistency(self):
        """Test that all URLs resolve correctly"""
        # Test dass alle URLs die wir in tests verwenden auch tatsächlich existieren
        url_names_to_test = [
            'offer-list',
            'offer-detail-list', 
            'order-list',
            'review-list',
            'base-info',
            'business-profiles-list',
            'customer-profiles-list'
        ]
        
        for url_name in url_names_to_test:
            try:
                url = reverse(url_name)
                self.assertIsNotNone(url)
                # Verify URL starts with /api/
                self.assertTrue(url.startswith('/api/'), 
                                f"URL {url_name} should start with /api/, got: {url}")
            except Exception as e:
                self.fail(f"Failed to reverse URL {url_name}: {e}")
    
    def test_parameterized_urls(self):
        """Test URLs that require parameters"""
        parameterized_urls = [
            ('offer-detail', {'pk': 1}),
            ('order-detail', {'pk': 1}), 
            ('review-detail', {'pk': 1}),
            ('profile-detail', {'pk': 1}),
            ('profile-by-user', {'pk': 1}),
            ('order-count', {'user_id': 1}),
            ('completed-order-count', {'user_id': 1}),
            ('business-reviews', {'business_user_id': 1}),
            ('reviewer-reviews', {'reviewer_id': 1}),
        ]
        
        for url_name, params in parameterized_urls:
            try:
                url = reverse(url_name, kwargs=params)
                self.assertIsNotNone(url)
                # Verify the parameter value appears in the URL
                param_value = str(list(params.values())[0])
                self.assertIn(param_value, url, 
                            f"Parameter {param_value} should appear in URL {url}")
            except Exception as e:
                self.fail(f"Failed to reverse parameterized URL {url_name} with {params}: {e}")


class URLAccessibilityTest(TestCase):
    """Test URL accessibility and basic responses"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com', 
            password='test123'
        )
    
    def test_public_urls_accessible(self):
        """Test that public URLs are accessible without authentication"""
        public_urls = [
            reverse('offer-list'),
            reverse('offer-detail-list'),
            reverse('review-list'),
            reverse('base-info'),
            reverse('business-profiles-list'),
            reverse('customer-profiles-list'),
        ]
        
        for url in public_urls:
            response = self.client.get(url)
            # Should be accessible (200) or at worst not require auth (not 401/403)
            self.assertNotEqual(response.status_code, 401, 
                                f"URL {url} should be accessible without auth")
            self.assertIn(response.status_code, [200, 404], 
                            f"URL {url} returned unexpected status: {response.status_code}")
    
    def test_authenticated_urls_require_auth(self):
        """Test that protected URLs require authentication"""
        protected_urls = [
            reverse('order-list'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            # Should require authentication
            self.assertEqual(response.status_code, 401, 
                            f"URL {url} should require authentication")
    
    def test_custom_action_urls_accessible(self):
        """Test that custom action URLs are accessible"""
        # Test with authenticated user for custom actions that might need it
        self.client.force_authenticate(user=self.user)
        
        custom_action_urls = [
            reverse('order-count', kwargs={'user_id': 1}),
            reverse('completed-order-count', kwargs={'user_id': 1}),
            reverse('business-reviews', kwargs={'business_user_id': 1}),
            reverse('reviewer-reviews', kwargs={'reviewer_id': 1}),
        ]
        
        for url in custom_action_urls:
            response = self.client.get(url)
            # Should not be method not allowed (405) or server error (500)
            self.assertNotEqual(response.status_code, 405, 
                                f"URL {url} should allow GET method")
            self.assertNotEqual(response.status_code, 500, 
                                f"URL {url} should not cause server error")
            # Acceptable responses: 200 (success), 404 (not found), 400 (bad request)
            self.assertIn(response.status_code, [200, 404, 400], 
                            f"URL {url} returned unexpected status: {response.status_code}")
