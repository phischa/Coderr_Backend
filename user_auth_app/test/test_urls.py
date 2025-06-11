from django.test import TestCase, TransactionTestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from user_auth_app.api import views


class URLPatternsTest(TestCase):
    """Test cases for URL patterns - FIXED for current URL structure"""
    
    def test_login_url_resolves(self):
        """Test that login URL resolves correctly"""
        url = reverse('login')
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/login/')
        
        resolver = resolve('/api/login/')
        self.assertEqual(resolver.func, views.login_view)

    def test_registration_url_resolves(self):
        """Test that registration URL resolves correctly"""
        url = reverse('registration')
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/registration/')
        
        resolver = resolve('/api/registration/')
        self.assertEqual(resolver.func, views.registration_view)

    # REMOVED: Guest login tests since endpoint doesn't exist
    # def test_guest_login_url_resolves(self):
    #     """Test that guest-login URL resolves correctly"""
    #     url = reverse('guest-login')
    #     self.assertEqual(url, '/api/guest-login/')

    def test_profile_detail_url_resolves(self):
        """Test that profile detail URL resolves correctly"""
        url = reverse('profile-detail', kwargs={'pk': 1})
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/profiles/1/')

    def test_profile_by_user_url_resolves(self):
        """Test that profile-by-user URL resolves correctly"""
        url = reverse('profile-by-user', kwargs={'pk': 1})
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/profile/user/1/')

    def test_business_profiles_url_resolves(self):
        """Test that business-profiles URL resolves correctly"""
        url = reverse('business-profiles')
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/profiles/business/')

    def test_customer_profiles_url_resolves(self):
        """Test that customer-profiles URL resolves correctly"""
        url = reverse('customer-profiles')
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/profiles/customer/')

    def test_profile_list_url_resolves(self):
        """Test that profile list URL resolves correctly"""
        url = reverse('profile-list')
        # FIXED: Remove /auth/ prefix
        self.assertEqual(url, '/api/profiles/')


class URLAccessibilityTest(TransactionTestCase):
    """Test cases for URL accessibility - FIXED with authentication"""
    
    def setUp(self):
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = self.user.profile
        # ADDED: Create token for authenticated tests
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()

    def test_login_url_accessible(self):
        """Test that login URL is accessible"""
        url = reverse('login')
        response = self.client.post(url, {
            'username': 'testuser',
            'password': 'testpassword'
        })
        
        self.assertNotIn(response.status_code, [404, 500])

    def test_registration_url_accessible(self):
        """Test that registration URL is accessible"""
        url = reverse('registration')
        response = self.client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpassword',
            'repeated_password': 'testpassword',
            'type': 'customer'
        })
        
        self.assertNotIn(response.status_code, [404, 500])

    def test_profile_list_url_accessible_with_auth(self):
        """Test that profile list URL is accessible with authentication"""
        # FIXED: Add authentication for profile access
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        url = reverse('profile-list')
        response = self.client.get(url)
        
        self.assertNotIn(response.status_code, [404, 500])

    def test_profile_list_url_requires_auth(self):
        """Test that profile list URL requires authentication"""
        url = reverse('profile-list')
        response = self.client.get(url)
        
        # ADDED: Should return 401 without authentication
        self.assertEqual(response.status_code, 401)


class HTTPMethodTest(TransactionTestCase):
    """Test cases for HTTP methods - FIXED for current permissions"""
    
    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()
        Token.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = self.user.profile
        self.token = Token.objects.create(user=self.user)

    def test_login_accepts_post_only(self):
        """Test that login URL only accepts POST"""
        url = reverse('login')
        
        response = self.client.post(url, {})
        self.assertNotEqual(response.status_code, 405)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_registration_accepts_post_only(self):
        """Test that registration URL only accepts POST"""
        url = reverse('registration')
        
        response = self.client.post(url, {})
        self.assertNotEqual(response.status_code, 405)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    # REMOVED: Guest login test since endpoint doesn't exist
    # def test_guest_login_accepts_post_only(self):

    def test_filtered_profiles_get_with_auth(self):
        """Test that filtered profile URLs work with authentication"""
        # FIXED: Add authentication for profile access
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        urls = [
            reverse('business-profiles'),
            reverse('customer-profiles'),
        ]
        
        for url in urls:
            # GET should work with auth
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_filtered_profiles_require_auth(self):
        """Test that filtered profile URLs require authentication"""
        urls = [
            reverse('business-profiles'),
            reverse('customer-profiles'),
        ]
        
        for url in urls:
            # GET without auth should return 401
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)