from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
import json

from user_auth_app.models import Profile


class LoginViewTest(TransactionTestCase):
    """Test cases for login_view"""
    
    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()  # Clean slate
        
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

    def test_token_creation(self):
        """Test that authentication token is created/retrieved"""
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        
        response1 = self.client.post(self.login_url, data, format='json')
        token1 = response1.data['token']
        
        response2 = self.client.post(self.login_url, data, format='json')
        token2 = response2.data['token']
        
        self.assertEqual(token1, token2)


class RegistrationViewTest(TransactionTestCase):
    """Test cases for registration_view"""
    
    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()  # Clean slate
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

    def test_password_mismatch(self):
        """Test registration with password mismatch"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpassword123',
            'repeated_password': 'differentpassword',
            'type': 'customer'
        }
        
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileViewSetTest(TransactionTestCase):
    """Test cases for ProfileViewSet - using TransactionTestCase for complete isolation"""
    
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

    def test_list_profiles_authenticated(self):
        """Test listing profiles when authenticated"""
        # Clean check - make sure we only have our 2 profiles
        profile_count = Profile.objects.count()
        self.assertEqual(profile_count, 2, f"Expected 2 profiles in clean setup, got {profile_count}")
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        url = reverse('profile-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # We should get exactly 2 profiles
        actual_count = len(response.data)
        self.assertEqual(actual_count, 2, f"Expected 2 profiles in response, got {actual_count}")

    def test_retrieve_profile(self):
        """Test retrieving specific profile"""
        url = reverse('profile-detail', kwargs={'pk': self.profile1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'user1')
        self.assertEqual(response.data['type'], 'business')

    def test_business_profiles_filter(self):
        """Test filtering business profiles"""
        url = reverse('business-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # We have 1 business profile
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['type'], 'business')

    def test_customer_profiles_filter(self):
        """Test filtering customer profiles"""
        url = reverse('customer-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # We have 1 customer profile
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['type'], 'customer')


class GuestLoginViewTest(TransactionTestCase):
    """Test cases for GuestLoginView"""
    
    def setUp(self):
        self.client = APIClient()
        self.guest_login_url = reverse('guest-login')

    def test_successful_guest_login(self):
        """Test successful guest login"""
        response = self.client.post(self.guest_login_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)
        self.assertIn('username', response.data)
        self.assertIn('is_guest', response.data)
        self.assertIn('type', response.data)
        
        self.assertEqual(response.data['status'], 'success')
        self.assertTrue(response.data['is_guest'])
        self.assertEqual(response.data['type'], 'customer')
        
        username = response.data['username']
        self.assertTrue(username.startswith('guest_'))

    def test_guest_user_creation(self):
        """Test that guest user is properly created"""
        response = self.client.post(self.guest_login_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user_id = response.data['user_id']
        user = User.objects.get(id=user_id)
        
        self.assertTrue(user.username.startswith('guest_'))
        self.assertTrue(user.email.startswith('guest_'))
        self.assertTrue(user.email.endswith('@example.com'))
        
        profile = user.profile
        self.assertTrue(profile.is_guest)
        self.assertEqual(profile.type, 'customer')

    def test_multiple_guest_logins(self):
        """Test that multiple guest logins create different users"""
        response1 = self.client.post(self.guest_login_url)
        response2 = self.client.post(self.guest_login_url)
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        self.assertNotEqual(response1.data['user_id'], response2.data['user_id'])
        self.assertNotEqual(response1.data['username'], response2.data['username'])
        self.assertNotEqual(response1.data['token'], response2.data['token'])
        