from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from user_auth_app.models import Profile
import json


class ProfileAPITestCase(TestCase):
    """
    Comprehensive test suite for Profile API endpoints
    """
    
    def setUp(self):
        """Set up test users and profiles"""
        # Create two test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass456',
            first_name='Jane',
            last_name='Smith'
        )
        
        # Update profiles
        self.profile1 = self.user1.profile
        self.profile1.type = 'business'
        self.profile1.location = 'Berlin'
        self.profile1.tel = '123456789'
        self.profile1.save()
        
        self.profile2 = self.user2.profile
        self.profile2.type = 'customer'
        self.profile2.save()
        
        # Create tokens
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        
        # Initialize API client
        self.client = APIClient()
    
    def test_get_profile_authenticated(self):
        """Test GET /api/profile/{pk}/ with authentication - should return 200"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.get(f'/api/profile/{self.user1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check that no fields are null (should be empty strings)
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['location'], 'Berlin')
        self.assertEqual(data['tel'], '123456789')
        self.assertEqual(data['description'], '')  # Should be empty string, not null
        self.assertEqual(data['working_hours'], '')  # Should be empty string, not null
        
        # Verify data types
        self.assertIsInstance(data['description'], str)
        self.assertIsInstance(data['working_hours'], str)
    
    def test_get_profile_unauthenticated(self):
        """Test GET /api/profile/{pk}/ without authentication - should return 401"""
        response = self.client.get(f'/api/profile/{self.user1.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_own_profile(self):
        """Test PATCH /api/profile/{pk}/ for own profile - should return 200"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        update_data = {
            'first_name': 'John Updated',
            'location': 'Munich',
            'description': 'New business description'
        }
        
        response = self.client.patch(
            f'/api/profile/{self.user1.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify updates
        self.assertEqual(data['first_name'], 'John Updated')
        self.assertEqual(data['location'], 'Munich')
        self.assertEqual(data['description'], 'New business description')
        
        # Verify unchanged fields still return empty strings, not null
        self.assertEqual(data['working_hours'], '')
    
    def test_update_other_users_profile(self):
        """Test PATCH /api/profile/{pk}/ for another user's profile - should return 403"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        update_data = {
            'first_name': 'Hacker',
            'location': 'Evil Location'
        }
        
        response = self.client.patch(
            f'/api/profile/{self.user2.id}/',  # Trying to update user2's profile
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.json())
    
    def test_update_profile_unauthenticated(self):
        """Test PATCH /api/profile/{pk}/ without authentication - should return 401"""
        update_data = {
            'first_name': 'Anonymous',
            'location': 'Unknown'
        }
        
        response = self.client.patch(
            f'/api/profile/{self.user1.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_not_found(self):
        """Test GET /api/profile/{pk}/ with non-existent user - should return 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        response = self.client.get('/api/profile/99999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_empty_string_fields_on_update(self):
        """Test that empty strings are saved correctly, not as null"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
        
        # First, set some values
        update_data = {
            'location': '',
            'tel': '',
            'description': '',
            'working_hours': ''
        }
        
        response = self.client.patch(
            f'/api/profile/{self.user1.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # All fields should be empty strings, not null
        self.assertEqual(data['location'], '')
        self.assertEqual(data['tel'], '')
        self.assertEqual(data['description'], '')
        self.assertEqual(data['working_hours'], '')
        
        # Verify in database
        self.user1.profile.refresh_from_db()
        self.assertEqual(self.user1.profile.location, '')
        self.assertEqual(self.user1.profile.tel, '')
    
    def test_guest_user_cannot_update_profile(self):
        """Test that guest users cannot update profiles"""
        # Create a guest user
        guest_user = User.objects.create_user(
            username='guest_customer_12345',
            email='guest@example.com',
            password='temppass'
        )
        guest_user.profile.is_guest = True
        guest_user.profile.save()
        
        guest_token = Token.objects.create(user=guest_user)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {guest_token.key}')
        
        update_data = {'first_name': 'Guest Update'}
        
        response = self.client.patch(
            f'/api/profile/{guest_user.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Guest users cannot update profiles', response.json()['error'])
