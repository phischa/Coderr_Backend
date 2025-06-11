from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
import json

from user_auth_app.models import Profile


class AuthenticationIntegrationTest(TransactionTestCase):
    """Integration tests for authentication flow - FIXED"""

    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()

    def test_complete_registration_login_flow(self):
        """Test complete flow: registration -> profile access -> update"""
        # Step 1: Register
        registration_data = {
            'username': 'integrationuser',
            'email': 'integration@example.com',
            'password': 'testpassword123',
            'repeated_password': 'testpassword123',
            'type': 'business',
            'first_name': 'Integration',
            'last_name': 'User'
        }

        registration_url = reverse('registration')
        reg_response = self.client.post(
            registration_url, registration_data, format='json')

        self.assertEqual(reg_response.status_code, status.HTTP_200_OK)
        self.assertIn('token', reg_response.data)

        registration_token = reg_response.data['token']
        user_id = reg_response.data['user_id']

        # Step 2: Use registration token to access profile
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {registration_token}')

        profile_url = reverse('profile-by-user', kwargs={'pk': user_id})
        profile_response = self.client.get(profile_url)

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['username'], 'integrationuser')
        self.assertEqual(profile_response.data['type'], 'business')

        # Step 3: Update profile
        update_data = {
            'location': 'Updated Location',
            'description': 'Updated Description',
            'first_name': 'Updated'
        }

        update_response = self.client.patch(
            profile_url, update_data, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

    # REMOVED: Guest login test since endpoint doesn't exist
    # def test_guest_to_regular_user_flow(self):


# Fix for user_auth_app/test/test_integration.py
# ProfileFilteringTest class

class ProfileFilteringTest(TransactionTestCase):
    """Test profile filtering functionality - FIXED for authentication"""

    def setUp(self):
        self.client = APIClient()

        # Complete clean slate
        User.objects.all().delete()
        Profile.objects.all().delete()
        Token.objects.all().delete()

        # Create test user for authentication
        self.auth_user = User.objects.create_user(
            username='authuser',
            email='auth@example.com',
            password='password'
        )
        # FIXED: Set auth user to business type to avoid counting in customer filter
        auth_profile = self.auth_user.profile
        auth_profile.type = 'business'
        auth_profile.save()
        
        self.auth_token = Token.objects.create(user=self.auth_user)

        # Create exactly what we need for testing
        # 3 business profiles (including auth_user)
        self.business_users = [self.auth_user]  # Include auth user
        for i in range(2):  # Create 2 more to get total of 3
            user = User.objects.create_user(
                username=f'business{i}',
                email=f'business{i}@example.com',
                password='password'
            )
            profile = user.profile
            profile.type = 'business'
            profile.location = f'Business Location {i}'
            profile.save()
            self.business_users.append(user)

        # 2 customer profiles (excluding auth_user)
        self.customer_users = []
        for i in range(2):
            user = User.objects.create_user(
                username=f'customer{i}',
                email=f'customer{i}@example.com',
                password='password'
            )
            profile = user.profile
            profile.type = 'customer'
            profile.location = f'Customer Location {i}'
            profile.save()
            self.customer_users.append(user)

    def test_all_profiles_requires_auth(self):
        """Test that getting all profiles requires authentication"""
        all_profiles_url = reverse('profile-list')
        all_response = self.client.get(all_profiles_url)

        # Should require authentication
        self.assertEqual(all_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_all_profiles_authenticated(self):
        """Test getting all profiles with authentication"""
        # Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.auth_token.key}')
        
        business_count = Profile.objects.filter(type='business').count()
        customer_count = Profile.objects.filter(type='customer').count()
        total_expected = business_count + customer_count

        # Verify our test setup
        self.assertEqual(business_count, 3, f"Expected 3 business profiles (including auth), got {business_count}")
        self.assertEqual(customer_count, 2, f"Expected 2 customer profiles, got {customer_count}")

        all_profiles_url = reverse('profile-list')
        all_response = self.client.get(all_profiles_url)

        self.assertEqual(all_response.status_code, status.HTTP_200_OK)

        # Use results array for paginated response
        if isinstance(all_response.data, dict) and 'results' in all_response.data:
            actual_count = len(all_response.data['results'])
        else:
            actual_count = len(all_response.data)

        self.assertEqual(actual_count, total_expected,
                         f"Expected {total_expected} total profiles, got {actual_count}")

    def test_business_profiles_filter_authenticated(self):
        """Test filtering business profiles with authentication"""
        # Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.auth_token.key}')
        
        business_url = reverse('business-profiles')
        business_response = self.client.get(business_url)

        self.assertEqual(business_response.status_code, status.HTTP_200_OK)

        # Handle pagination
        if isinstance(business_response.data, dict) and 'results' in business_response.data:
            actual_count = len(business_response.data['results'])
            profiles_data = business_response.data['results']
        else:
            actual_count = len(business_response.data)
            profiles_data = business_response.data

        expected_count = len(self.business_users)  # Should be 3 (including auth user)
        self.assertEqual(actual_count, expected_count,
                         f"Expected {expected_count} business profiles, got {actual_count}")

        for profile in profiles_data:
            self.assertEqual(profile['type'], 'business')

    def test_customer_profiles_filter_authenticated(self):
        """Test filtering customer profiles with authentication - FIXED"""
        # Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.auth_token.key}')
        
        customer_url = reverse('customer-profiles')
        customer_response = self.client.get(customer_url)

        self.assertEqual(customer_response.status_code, status.HTTP_200_OK)

        # Handle pagination
        if isinstance(customer_response.data, dict) and 'results' in customer_response.data:
            actual_count = len(customer_response.data['results'])
            profiles_data = customer_response.data['results']
        else:
            actual_count = len(customer_response.data)
            profiles_data = customer_response.data

        expected_count = len(self.customer_users)  # Should be exactly 2 (auth user is business type)
        self.assertEqual(actual_count, expected_count,
                         f"Expected {expected_count} customer profiles, got {actual_count}")

        for profile in profiles_data:
            self.assertEqual(profile['type'], 'customer')

        # ADDITIONAL DEBUG INFO - can remove after verification
        total_customers_in_db = Profile.objects.filter(type='customer').count()
        self.assertEqual(total_customers_in_db, expected_count, 
                        f"DB should have {expected_count} customer profiles, but has {total_customers_in_db}")


class PerformanceTest(TransactionTestCase):
    """Performance tests - FIXED for authentication"""

    def setUp(self):
        self.client = APIClient()
        # Complete clean slate
        User.objects.all().delete()
        Profile.objects.all().delete()
        Token.objects.all().delete()
        
        # Create auth user
        self.auth_user = User.objects.create_user(
            username='authuser',
            email='auth@example.com',
            password='password'
        )
        self.auth_token = Token.objects.create(user=self.auth_user)

    def test_large_profile_list_performance_authenticated(self):
        """Test performance with many profiles - FIXED for authentication"""
        users_count = 20

        created_users = []
        for i in range(users_count):
            user = User.objects.create_user(
                username=f'perfuser{i}',
                email=f'perfuser{i}@example.com',
                password='password'
            )
            profile = user.profile
            profile.type = 'business' if i % 2 == 0 else 'customer'
            profile.location = f'Location {i}'
            profile.save()
            created_users.append(user)

        total_profiles = Profile.objects.count()
        total_users = User.objects.count()

        self.assertEqual(total_users, users_count + 1,  # +1 for auth user
                         f"Expected {users_count + 1} users in DB, got {total_users}")

        # FIXED: Add authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.auth_token.key}')
        
        profiles_url = reverse('profile-list')
        response = self.client.get(profiles_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'count' in response.data:
            total_count = response.data['count']
            self.assertEqual(total_count, users_count + 1,  # +1 for auth user
                             f"Expected {users_count + 1} total profiles, got {total_count}")

class EdgeCaseTest(TransactionTestCase):
    """Test edge cases and error scenarios"""

    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()

    def test_registration_with_existing_username(self):
        """Test registration with existing username"""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password'
        )

        registration_data = {
            'username': 'existing',
            'email': 'different@example.com',
            'password': 'password123',
            'repeated_password': 'password123',
            'type': 'customer'
        }

        registration_url = reverse('registration')
        response = self.client.post(
            registration_url, registration_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_inactive_user(self):
        """Test login with inactive user"""
        user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='password'
        )
        user.is_active = False
        user.save()

        login_data = {
            'username': 'inactiveuser',
            'password': 'password'
        }

        login_url = reverse('login')
        response = self.client.post(login_url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
