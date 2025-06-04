from django.test import TestCase, TransactionTestCase, APIClient
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from user_auth_app.api import views


class URLPatternsTest(TestCase):
    """Test cases for URL patterns - corrected for router vs direct paths"""
    
    def test_login_url_resolves(self):
        """Test that login URL resolves correctly"""
        url = reverse('login')
        self.assertEqual(url, '/api/auth/login/')
        
        resolver = resolve('/api/auth/login/')
        self.assertEqual(resolver.func, views.login_view)

    def test_registration_url_resolves(self):
        """Test that registration URL resolves correctly"""
        url = reverse('registration')
        self.assertEqual(url, '/api/auth/registration/')
        
        resolver = resolve('/api/auth/registration/')
        self.assertEqual(resolver.func, views.registration_view)

    def test_guest_login_url_resolves(self):
        """Test that guest-login URL resolves correctly"""
        url = reverse('guest-login')
        self.assertEqual(url, '/api/auth/guest-login/')

    def test_profile_detail_url_resolves(self):
        """Test that profile detail URL resolves correctly - Router takes precedence"""
        url = reverse('profile-detail', kwargs={'pk': 1})
        # Router creates 'profiles' (plural) not 'profile' (singular)
        self.assertEqual(url, '/api/auth/profiles/1/')

    def test_profile_by_user_url_resolves(self):
        """Test that profile-by-user URL resolves correctly"""
        url = reverse('profile-by-user', kwargs={'pk': 1})
        self.assertEqual(url, '/api/auth/profile/user/1/')

    def test_business_profiles_url_resolves(self):
        """Test that business-profiles URL resolves correctly"""
        url = reverse('business-profiles')
        self.assertEqual(url, '/api/auth/profiles/business/')

    def test_customer_profiles_url_resolves(self):
        """Test that customer-profiles URL resolves correctly"""
        url = reverse('customer-profiles')
        self.assertEqual(url, '/api/auth/profiles/customer/')

    def test_profile_list_url_resolves(self):
        """Test that profile list URL resolves correctly"""
        url = reverse('profile-list')
        self.assertEqual(url, '/api/auth/profiles/')


class URLAccessibilityTest(TransactionTestCase):
    """Test cases for URL accessibility - using TransactionTestCase for isolation"""
    
    def setUp(self):
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = self.user.profile

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

    def test_guest_login_url_accessible(self):
        """Test that guest-login URL is accessible"""
        url = reverse('guest-login')
        response = self.client.post(url)
        
        self.assertNotIn(response.status_code, [404, 500])

    def test_profile_list_url_accessible(self):
        """Test that profile list URL is accessible"""
        url = reverse('profile-list')
        response = self.client.get(url)
        
        self.assertNotIn(response.status_code, [404, 500])


class HTTPMethodTest(TransactionTestCase):
    """Test cases for HTTP methods on different URLs"""
    
    def setUp(self):
        User.objects.all().delete()
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

    def test_guest_login_accepts_post_only(self):
        """Test that guest-login URL only accepts POST"""
        url = reverse('guest-login')
        
        response = self.client.post(url)
        self.assertNotEqual(response.status_code, 405)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_filtered_profiles_get_vs_post(self):
        """Test that filtered profile URLs handle GET vs POST correctly"""
        urls = [
            reverse('business-profiles'),
            reverse('customer-profiles'),
        ]
        
        for url in urls:
            # GET should work
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 405)
            
            # POST without auth should return 401 (unauthorized)
            response = self.client.post(url, {})
            self.assertEqual(response.status_code, 401)

    def test_authenticated_post_to_filtered_profiles(self):
        """Test POST to filtered profiles with authentication"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        urls = [
            reverse('business-profiles'),
            reverse('customer-profiles'),
        ]
        
        for url in urls:
            # Even with auth, POST should not be allowed (405 Method Not Allowed)
            response = self.client.post(url, {})
            self.assertEqual(response.status_code, 405)
            