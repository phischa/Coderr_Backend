from unittest.mock import patch, PropertyMock
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from user_auth_app.models import Profile
from Coderr_app.api.permissions import IsBusinessUser, IsCustomerUser


class IsBusinessUserPermissionTest(TestCase):
    """Test IsBusinessUser permission"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.permission = IsBusinessUser()
        
        # Create business user - Profile is auto-created as 'customer', then we change it
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile was auto-created with type='customer', change to 'business'
        self.business_user.profile.type = 'business'
        self.business_user.profile.save()
        
        # Create customer user - Profile is auto-created as 'customer', keep it
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Profile is already 'customer' by default, no change needed
    
    def test_business_user_has_permission(self):
        """Test that business users have permission"""
        request = self.factory.get('/')
        request.user = self.business_user
        
        # Verify setup is correct
        self.assertTrue(request.user.is_authenticated)
        self.assertTrue(hasattr(request.user, 'profile'))
        self.assertEqual(request.user.profile.type, 'business')
        
        # Test permission
        has_permission = self.permission.has_permission(request, None)
        self.assertTrue(has_permission)
    
    def test_customer_user_no_permission(self):
        """Test that customer users don't have business permission"""
        request = self.factory.get('/')
        request.user = self.customer_user
        
        # Verify setup is correct
        self.assertTrue(request.user.is_authenticated)
        self.assertTrue(hasattr(request.user, 'profile'))
        self.assertEqual(request.user.profile.type, 'customer')
        
        # Test permission - customer should NOT have business permission
        has_permission = self.permission.has_permission(request, None)
        self.assertFalse(has_permission)
    
    def test_anonymous_user_no_permission(self):
        """Test that anonymous users don't have permission"""
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        # Verify setup is correct
        self.assertFalse(request.user.is_authenticated)
        
        # Test permission
        has_permission = self.permission.has_permission(request, None)
        self.assertFalse(has_permission)


class IsCustomerUserPermissionTest(TestCase):
    """Test IsCustomerUser permission"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.permission = IsCustomerUser()
        
        # Create business user - Profile is auto-created as 'customer', then we change it
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Profile was auto-created with type='customer', change to 'business'
        self.business_user.profile.type = 'business'
        self.business_user.profile.save()
        
        # Create customer user - Profile is auto-created as 'customer', keep it
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Profile is already 'customer' by default, no change needed
    
    def test_customer_user_has_permission(self):
        """Test that customer users have permission"""
        request = self.factory.get('/')
        request.user = self.customer_user
        
        # Verify setup is correct
        self.assertTrue(request.user.is_authenticated)
        self.assertTrue(hasattr(request.user, 'profile'))
        self.assertEqual(request.user.profile.type, 'customer')
        
        # Test permission
        has_permission = self.permission.has_permission(request, None)
        self.assertTrue(has_permission)
    
    def test_business_user_no_permission(self):
        """Test that business users don't have customer permission"""
        request = self.factory.get('/')
        request.user = self.business_user
        
        # Verify setup is correct
        self.assertTrue(request.user.is_authenticated)
        self.assertTrue(hasattr(request.user, 'profile'))
        self.assertEqual(request.user.profile.type, 'business')
        
        # Test permission - business should NOT have customer permission
        has_permission = self.permission.has_permission(request, None)
        self.assertFalse(has_permission)
    
    def test_anonymous_user_no_permission(self):
        """Test that anonymous users don't have permission"""
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        # Verify setup is correct
        self.assertFalse(request.user.is_authenticated)
        
        # Test permission
        has_permission = self.permission.has_permission(request, None)
        self.assertFalse(has_permission)


class PermissionIntegrationTest(TestCase):
    """Integration tests for permissions"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create business user
        self.business_user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        # Change auto-created profile from 'customer' to 'business'
        self.business_user.profile.type = 'business'
        self.business_user.profile.save()
        
        # Create customer user (profile is auto-created as 'customer')
        self.customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        # Profile is already 'customer' by default
    
    def test_permission_logic_consistency(self):
        """Test that the permissions work as expected together"""
        business_permission = IsBusinessUser()
        customer_permission = IsCustomerUser()
        
        # Business user tests
        request = self.factory.get('/')
        request.user = self.business_user
        
        self.assertTrue(business_permission.has_permission(request, None))
        self.assertFalse(customer_permission.has_permission(request, None))
        
        # Customer user tests  
        request.user = self.customer_user
        
        self.assertFalse(business_permission.has_permission(request, None))
        self.assertTrue(customer_permission.has_permission(request, None))
    
    def test_automatic_profile_creation(self):
        """Test that profiles are automatically created for users"""
        # Create a new user
        new_user = User.objects.create_user(
            username='newuser',
            email='new@test.com',
            password='testpass123'
        )
        
        # Profile should exist automatically
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertEqual(new_user.profile.type, 'customer')  # Default type
        
        # hasattr should always return True for users with auto-created profiles
        self.assertTrue(hasattr(new_user, 'profile'))
        
        # Profile should be accessible without DoesNotExist
        profile = new_user.profile
        self.assertIsInstance(profile, Profile)
        self.assertEqual(profile.user, new_user)
    
    def test_permission_with_different_profile_types(self):
        """Test permissions work correctly with profile type changes"""
        business_permission = IsBusinessUser()
        customer_permission = IsCustomerUser()
        
        # Create user (will have 'customer' profile by default)
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        request = self.factory.get('/')
        request.user = user
        
        # Initially should be customer
        self.assertFalse(business_permission.has_permission(request, None))
        self.assertTrue(customer_permission.has_permission(request, None))
        
        # Change to business
        user.profile.type = 'business'
        user.profile.save()
        
        # Now should be business
        self.assertTrue(business_permission.has_permission(request, None))
        self.assertFalse(customer_permission.has_permission(request, None))
        
        # Change back to customer
        user.profile.type = 'customer'
        user.profile.save()
        
        # Should be customer again
        self.assertFalse(business_permission.has_permission(request, None))
        self.assertTrue(customer_permission.has_permission(request, None))


class ProfileSignalTest(TestCase):
    """Test the automatic profile creation signal"""
    
    def test_profile_created_on_user_creation(self):
        """Test that profile is automatically created when user is created"""
        # Count profiles before
        initial_count = Profile.objects.count()
        
        # Create user
        user = User.objects.create_user(
            username='signaltest',
            email='signal@test.com',
            password='testpass123'
        )
        
        # Profile should be created automatically
        self.assertEqual(Profile.objects.count(), initial_count + 1)
        
        # Profile should exist and be accessible
        self.assertTrue(hasattr(user, 'profile'))
        profile = user.profile
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.type, 'customer')  # Default type
    
    def test_default_profile_type_is_customer(self):
        """Test that new profiles default to customer type"""
        user = User.objects.create_user(
            username='defaulttest',
            email='default@test.com',
            password='testpass123'
        )
        
        self.assertEqual(user.profile.type, 'customer')
    
    def test_multiple_users_get_separate_profiles(self):
        """Test that each user gets their own profile"""
        user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        
        user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        
        # Each should have their own profile
        self.assertNotEqual(user1.profile.id, user2.profile.id)
        self.assertEqual(user1.profile.user, user1)
        self.assertEqual(user2.profile.user, user2)
        
        # Both should be customer by default
        self.assertEqual(user1.profile.type, 'customer')
        self.assertEqual(user2.profile.type, 'customer')

class PermissionExceptionHandlingTestFixed(TestCase):
    """Fixed test for Permission DoesNotExist exception handling"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.business_permission = IsBusinessUser()
        self.customer_permission = IsCustomerUser()
    
    def test_business_permission_profile_does_not_exist(self):
        """Test IsBusinessUser when Profile.DoesNotExist (Zeilen 15-16)"""
        user = User.objects.create_user(
            username='test_business',
            email='test@test.com',
            password='test123'
        )
        
        with patch.object(type(user), 'profile', new_callable=PropertyMock) as mock_profile:
            mock_profile.side_effect = Profile.DoesNotExist()
            
            request = self.factory.get('/')
            request.user = user
            
            result = self.business_permission.has_permission(request, None)
            self.assertFalse(result)
    
    def test_customer_permission_profile_does_not_exist(self):
        """Test IsCustomerUser when Profile.DoesNotExist (Zeilen 29-30)"""
        user = User.objects.create_user(
            username='test_customer',
            email='test2@test.com',
            password='test123'
        )
        
        with patch.object(type(user), 'profile', new_callable=PropertyMock) as mock_profile:
            mock_profile.side_effect = Profile.DoesNotExist()
            
            request = self.factory.get('/')
            request.user = user
            
            result = self.customer_permission.has_permission(request, None)
            self.assertFalse(result)
