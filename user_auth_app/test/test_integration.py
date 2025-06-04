from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
import json

from user_auth_app.models import Profile


class AuthenticationIntegrationTest(TransactionTestCase):
    """Integration tests for authentication flow"""

    def setUp(self):
        self.client = APIClient()
        User.objects.all().delete()  # Clean slate

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

    def test_guest_to_regular_user_flow(self):
        """Test flow: guest login -> regular registration"""
        # Step 1: Guest login
        guest_url = reverse('guest-login')
        guest_response = self.client.post(guest_url)

        self.assertEqual(guest_response.status_code, status.HTTP_200_OK)
        self.assertTrue(guest_response.data['is_guest'])

        guest_user_id = guest_response.data['user_id']

        # Step 2: Register as regular user
        self.client.credentials()  # Clear credentials

        registration_data = {
            'username': 'regularuser',
            'email': 'regular@example.com',
            'password': 'password123',
            'repeated_password': 'password123',
            'type': 'customer'
        }

        registration_url = reverse('registration')
        reg_response = self.client.post(
            registration_url, registration_data, format='json')

        self.assertEqual(reg_response.status_code, status.HTTP_200_OK)

        # Verify both users exist and are different
        guest_user = User.objects.get(id=guest_user_id)
        regular_user = User.objects.get(id=reg_response.data['user_id'])

        self.assertNotEqual(guest_user.id, regular_user.id)
        self.assertTrue(guest_user.profile.is_guest)
        self.assertFalse(regular_user.profile.is_guest)


class ProfileFilteringTest(TransactionTestCase):
    """Test profile filtering functionality with complete isolation"""

    def setUp(self):
        self.client = APIClient()

        # Complete clean slate
        User.objects.all().delete()
        Profile.objects.all().delete()
        Token.objects.all().delete()

        # Create exactly what we need for testing
        # 3 business profiles
        self.business_users = []
        for i in range(3):
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

        # 2 customer profiles
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

    def test_all_profiles(self):
        """Test getting all profiles - FIXED for pagination"""
        business_count = Profile.objects.filter(type='business').count()
        customer_count = Profile.objects.filter(type='customer').count()
        total_expected = business_count + customer_count

        all_profiles_url = reverse('profile-list')
        all_response = self.client.get(all_profiles_url)

        self.assertEqual(all_response.status_code, status.HTTP_200_OK)

        # FIX: Use results array for paginated response
        if isinstance(all_response.data, dict) and 'results' in all_response.data:
            actual_count = len(all_response.data['results'])
        else:
            actual_count = len(all_response.data)  # Fallback for non-paginated

        self.assertEqual(actual_count, total_expected,
                         f"Expected {total_expected} total profiles, got {actual_count}")

    def test_business_profiles_filter(self):
        """Test filtering business profiles - FIXED"""
        business_url = reverse('business-profiles')
        business_response = self.client.get(business_url)

        self.assertEqual(business_response.status_code, status.HTTP_200_OK)

        # FIX: Handle pagination
        if isinstance(business_response.data, dict) and 'results' in business_response.data:
            actual_count = len(business_response.data['results'])
            profiles_data = business_response.data['results']
        else:
            actual_count = len(business_response.data)
            profiles_data = business_response.data

        expected_count = len(self.business_users)
        self.assertEqual(actual_count, expected_count,
                         f"Expected {expected_count} business profiles, got {actual_count}")

        for profile in profiles_data:
            self.assertEqual(profile['type'], 'business')

    def test_customer_profiles_filter(self):
        """Test filtering customer profiles - FIXED"""
        customer_url = reverse('customer-profiles')
        customer_response = self.client.get(customer_url)

        self.assertEqual(customer_response.status_code, status.HTTP_200_OK)

        # FIX: Handle pagination
        if isinstance(customer_response.data, dict) and 'results' in customer_response.data:
            actual_count = len(customer_response.data['results'])
            profiles_data = customer_response.data['results']
        else:
            actual_count = len(customer_response.data)
            profiles_data = customer_response.data

        expected_count = len(self.customer_users)
        self.assertEqual(actual_count, expected_count,
                         f"Expected {expected_count} customer profiles, got {actual_count}")

        for profile in profiles_data:
            self.assertEqual(profile['type'], 'customer')


class PerformanceTest(TransactionTestCase):
    """Performance tests with complete isolation"""

    def setUp(self):
        self.client = APIClient()
        # Complete clean slate
        User.objects.all().delete()
        Profile.objects.all().delete()
        Token.objects.all().delete()

    def test_large_profile_list_performance(self):
        """Test performance with many profiles - pagination aware"""
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

        self.assertEqual(total_users, users_count,
                         f"Expected {users_count} users in DB, got {total_users}")
        self.assertEqual(total_profiles, users_count,
                         f"Expected {users_count} profiles in DB, got {total_profiles}")

        profiles_url = reverse('profile-list')
        response = self.client.get(profiles_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'count' in response.data:
            total_count = response.data['count']
            self.assertEqual(total_count, users_count,
                             f"Expected {users_count} total profiles, got {total_count}")

            if isinstance(response.data, dict) and 'results' in response.data:
                results_count = len(response.data['results'])
            else:
                results_count = len(response.data)
            expected_first_page = min(6, users_count)
            self.assertEqual(results_count, expected_first_page,
                             f"Expected {expected_first_page} profiles in first page, got {results_count}")
            self.assertIn('next', response.data,
                          "Paginated response should have 'next' field")
            self.assertIn('previous', response.data,
                          "Paginated response should have 'previous' field")

            if users_count > 6:
                self.assertIsNotNone(
                    response.data['next'], "Should have next page with more than 6 profiles")
            else:
                self.assertIsNone(
                    response.data['next'], "Should not have next page with 6 or fewer profiles")

        else:
            actual_response_count = len(response.data)
            self.assertEqual(actual_response_count, users_count,
                             f"Expected {users_count} profiles in response, got {actual_response_count}")

    def test_rapid_guest_user_creation(self):
        """Test rapid creation of guest users"""
        guest_url = reverse('guest-login')

        initial_count = User.objects.filter(
            username__startswith='guest_').count()
        guest_count = 10
        for _ in range(guest_count):
            response = self.client.post(guest_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        final_count = User.objects.filter(
            username__startswith='guest_').count()
        self.assertEqual(final_count, initial_count + guest_count)


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

    def test_concurrent_guest_logins(self):
        """Test multiple concurrent guest logins"""
        responses = []
        for _ in range(5):
            guest_url = reverse('guest-login')
            response = self.client.post(guest_url)
            responses.append(response)

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        usernames = {r.data['username'] for r in responses}
        self.assertEqual(len(usernames), 5)  # All unique


class DataConsistencyTest(TransactionTestCase):
    """Test data consistency and integrity"""

    def setUp(self):
        User.objects.all().delete()

    def test_profile_creation_signal_consistency(self):
        """Test that profile is always created when user is created"""
        user = User.objects.create_user(
            username='signaltest',
            email='signal@example.com',
            password='password'
        )

        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.user, user)

    def test_token_user_relationship(self):
        """Test token-user relationship integrity"""
        user = User.objects.create_user(
            username='tokentest',
            email='token@example.com',
            password='password'
        )

        token = Token.objects.create(user=user)

        self.assertEqual(token.user, user)
        self.assertEqual(user.auth_token, token)

    def test_profile_user_cascade_delete(self):
        """Test that profile is deleted when user is deleted"""
        user = User.objects.create_user(
            username='cascadetest',
            email='cascade@example.com',
            password='password'
        )

        profile_id = user.profile.id
        user.delete()

        with self.assertRaises(Profile.DoesNotExist):
            Profile.objects.get(pk=profile_id)
