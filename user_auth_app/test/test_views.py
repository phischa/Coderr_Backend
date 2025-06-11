from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
import json

from user_auth_app.models import Profile


class LoginViewTest(TransactionTestCase):
    """Test cases for login_view - UNCHANGED"""
    
    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.profile = self.user.profile
        self.profile.type = 'customer'
        self.profile.save()
        
        self.login_url = reverse('login')

    def test_successful_login(self):
        """Test successful login with valid credentials"""
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)
        self.assertIn('username', response.data)
        self.assertIn('type', response.data)
        
        self.assertEqual(response.data['user_id'], self.user.id)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['type'], 'customer')

    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Invalid credentials')


class RegistrationViewTest(TransactionTestCase):
    """Test cases for registration_view - UNCHANGED"""
    
    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()
        self.registration_url = reverse('registration')

    def test_successful_registration(self):
        """Test successful user registration"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpassword123',
            'repeated_password': 'testpassword123',
            'type': 'business',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(self.registration_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)
        self.assertIn('username', response.data)
        self.assertIn('type', response.data)
        
        # Verify user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.profile.type, 'business')


class ProfileViewSetTest(TransactionTestCase):
    """Test cases for ProfileViewSet - FIXED for authentication requirements"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Complete clean slate
        User.objects.all().delete()
        Profile.objects.all().delete()
        Token.objects.all().delete()
        
        # Create exactly 2 test users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpassword'
        )
        self.profile1 = self.user1.profile
        self.profile1.type = 'business'
        self.profile1.save()
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpassword'
        )
        self.profile2 = self.user2.profile
        self.profile2.type = 'customer'
        self.profile2.save()
        
        self.token1 = Token.objects.create(user=self.user1)

    def test_list_profiles_requires_authentication(self):
        """Test that listing profiles requires authentication"""
        url = reverse('profile-list')
        response = self.client.get(url)
        
        # FIXED: Should require authentication
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_profiles_authenticated(self):
        """Test listing profiles when authenticated"""
        # Clean check - make sure we only have our 2 profiles
        profile_count = Profile.objects.count()
        self.assertEqual(profile_count, 2, f"Expected 2 profiles in clean setup, got {profile_count}")
        
        # FIXED: Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        url = reverse('profile-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        if isinstance(response.data, dict) and 'results' in response.data:
            actual_count = len(response.data['results'])
        else:
            actual_count = len(response.data)
        self.assertEqual(actual_count, 2, f"Expected 2 profiles in response, got {actual_count}")

    def test_retrieve_profile_requires_authentication(self):
        """Test that retrieving specific profile requires authentication"""
        url = reverse('profile-detail', kwargs={'pk': self.profile1.pk})
        response = self.client.get(url)
        
        # FIXED: Should require authentication
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_profile_authenticated(self):
        """Test retrieving specific profile with authentication"""
        # FIXED: Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        url = reverse('profile-detail', kwargs={'pk': self.profile1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'user1')
        self.assertEqual(response.data['type'], 'business')

    def test_business_profiles_filter_requires_auth(self):
        """Test that business profiles filter requires authentication"""
        url = reverse('business-profiles')
        response = self.client.get(url)
        
        # FIXED: Should require authentication
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_profiles_filter_authenticated(self):
        """Test filtering business profiles with authentication"""
        # FIXED: Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        url = reverse('business-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # We have 1 business profile
        if isinstance(response.data, dict) and 'results' in response.data:
            profiles_data = response.data['results']
        else:
            profiles_data = response.data
            
        self.assertEqual(len(profiles_data), 1)
        self.assertEqual(profiles_data[0]['type'], 'business')

    def test_customer_profiles_filter_authenticated(self):
        """Test filtering customer profiles with authentication"""
        # FIXED: Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        url = reverse('customer-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # We have 1 customer profile
        if isinstance(response.data, dict) and 'results' in response.data:
            profiles_data = response.data['results']
        else:
            profiles_data = response.data
            
        self.assertEqual(len(profiles_data), 1)
        self.assertEqual(profiles_data[0]['type'], 'customer')
        