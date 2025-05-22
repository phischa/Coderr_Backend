from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from user_auth_app.models import Profile
from user_auth_app.api.serializers import (
    UserSerializer, ProfileSerializer, 
    ProfileUpdateSerializer, RegistrationSerializer
)

class ProfileModelTestCase(TestCase):
    """
    Test case for the Profile model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.testuser = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User'
        )
        self.profile = self.testuser.profile
        self.profile.type = 'customer'
        self.profile.location = 'Berlin, Germany'
        self.profile.tel = '+49123456789'
        self.profile.save()
    
    def test_profile_creation(self):
        """Test if profile is created correctly."""
        self.assertEqual(self.profile.user, self.testuser)
        self.assertEqual(self.profile.type, 'customer')
        self.assertEqual(self.profile.location, 'Berlin, Germany')
        self.assertEqual(self.profile.tel, '+49123456789')
        self.assertFalse(self.profile.is_guest)
    
    def test_profile_properties(self):
        """Test profile properties."""
        self.assertEqual(self.profile.username, 'testuser')
        self.assertEqual(self.profile.first_name, 'Test')
        self.assertEqual(self.profile.last_name, 'User')
        self.assertEqual(self.profile.email, 'test@example.com')
    
    def test_profile_str_method(self):
        """Test the __str__ method of profile."""
        expected_str = f"testuser (customer)"
        self.assertEqual(str(self.profile), expected_str)


class ProfileSerializerTestCase(TestCase):
    """
    Test case for the Profile serializers.
    """
    
    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepassword123',
            'repeated_password': 'securepassword123',
            'type': 'customer',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        self.testuser = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='existingpassword123',
            first_name='Existing',
            last_name='User'
        )
        self.profile = self.testuser.profile
        self.profile.type = 'business'
        self.profile.location = 'Munich, Germany'
        self.profile.save()
    
    def test_registration_serializer(self):
        """Test the RegistrationSerializer."""
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.profile.type, 'customer')
    
    def test_profile_serializer(self):
        """Test the ProfileSerializer."""
        serializer = ProfileSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data['username'], 'existinguser')
        self.assertEqual(data['first_name'], 'Existing')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['type'], 'business')
        self.assertEqual(data['location'], 'Munich, Germany')
    
    def test_profile_update_serializer(self):
        """Test the ProfileUpdateSerializer."""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'location': 'Hamburg, Germany',
            'tel': '+49987654321'
        }
        
        serializer = ProfileUpdateSerializer(self.profile, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()
        
        # Reload profile to see changes
        updated_profile.user.refresh_from_db()
        updated_profile.refresh_from_db()
        
        self.assertEqual(updated_profile.user.first_name, 'Updated')
        self.assertEqual(updated_profile.user.last_name, 'Name')
        self.assertEqual(updated_profile.user.email, 'updated@example.com')
        self.assertEqual(updated_profile.location, 'Hamburg, Germany')
        self.assertEqual(updated_profile.tel, '+49987654321')


class ProfileAPITestCase(APITestCase):
    """
    Test case for the Profile API endpoints.
    """
    
    def setUp(self):
        """Set up test data and client."""
        self.client = APIClient()
        
        # Create business user
        self.business_user = User.objects.create_user(
            username='business',
            email='business@example.com',
            password='business123',
            first_name='Business',
            last_name='Owner'
        )
        self.business_profile = self.business_user.profile
        self.business_profile.type = 'business'
        self.business_profile.location = 'Frankfurt, Germany'
        self.business_profile.description = 'A sample business'
        self.business_profile.save()
        self.business_token = Token.objects.create(user=self.business_user)
        
        # Create customer user
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='customer123',
            first_name='Regular',
            last_name='Customer'
        )
        self.customer_profile = self.customer_user.profile
        self.customer_profile.type = 'customer'
        self.customer_profile.save()
        self.customer_token = Token.objects.create(user=self.customer_user)
    
    def test_profile_list(self):
        """Test profile list endpoint."""
        url = reverse('profile-list')
        response = self.client.get(url)
    
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Für paginierte Response:
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)
    
    def test_profile_detail(self):
        """Test profile detail endpoint."""
        url = reverse('profile-detail', kwargs={'pk': self.business_profile.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'business')
        self.assertEqual(response.data['type'], 'business')
    
    def test_profile_by_user_id(self):
        """Test profile by user ID endpoint."""
        url = reverse('profile-by-user', kwargs={'pk': self.customer_user.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'customer')
        self.assertEqual(response.data['type'], 'customer')
    
    def test_business_profiles(self):
        """Test business profiles endpoint."""
        url = reverse('business-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'business')
    
    def test_customer_profiles(self):
        """Test customer profiles endpoint."""
        url = reverse('customer-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'customer')
    
    def test_update_profile(self):
        """Test profile update."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.business_token.key}')
        url = reverse('profile-detail', kwargs={'pk': self.business_profile.id})
        
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Business',
            'location': 'Cologne, Germany',
            'working_hours': 'Mon-Fri 9:00-18:00'
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload profile
        self.business_user.refresh_from_db()
        self.business_profile.refresh_from_db()
        
        self.assertEqual(self.business_user.first_name, 'Updated')
        self.assertEqual(self.business_user.last_name, 'Business')
        self.assertEqual(self.business_profile.location, 'Cologne, Germany')
        self.assertEqual(self.business_profile.working_hours, 'Mon-Fri 9:00-18:00')


class AuthenticationTestCase(APITestCase):
    """
    Test case for authentication functions.
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.login_url = reverse('login')
        self.register_url = reverse('registration')
        self.guest_login_url = reverse('guest-login')
        
        self.user = User.objects.create_user(
            username='testlogin',
            email='testlogin@example.com',
            password='testlogin123'
        )
        self.profile = self.user.profile
        self.profile.type = 'customer'
        self.profile.save()
    
    def test_registration(self):
        """Test user registration."""
        data = {
            'username': 'newregistered',
            'email': 'new@example.com',
            'password': 'testpass123',
            'repeated_password': 'testpass123',
            'type': 'business',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'newregistered')
        self.assertEqual(response.data['type'], 'business')
        
        # Check if user exists in database
        self.assertTrue(User.objects.filter(username='newregistered').exists())
    
    def test_login(self):
        """Test user login."""
        data = {
            'username': 'testlogin',
            'password': 'testlogin123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'testlogin')
    
    def test_guest_login(self):
        """Test guest login."""
        response = self.client.post(self.guest_login_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertTrue(response.data['is_guest'])
        
        # Check if guest profile was created
        guest_username = response.data['username']
        guest_user = User.objects.get(username=guest_username)
        self.assertTrue(guest_user.profile.is_guest)
        self.assertEqual(guest_user.profile.type, 'customer')


class UserSerializerTestCase(TestCase):
    """
    Test case for the UserSerializer.
    """
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='userserializertest',
            email='userserializer@example.com',
            password='test12345',
            first_name='User',
            last_name='Serializer'
        )
        self.profile = self.user.profile
        self.profile.type = 'customer'
        self.profile.save()
    
    def test_user_serializer(self):
        """Test the UserSerializer."""
        serializer = UserSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data['username'], 'userserializertest')
        self.assertEqual(data['first_name'], 'User')
        self.assertEqual(data['last_name'], 'Serializer')
        self.assertEqual(data['email'], 'userserializer@example.com')
        self.assertTrue('id' in data)