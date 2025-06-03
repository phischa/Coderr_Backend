from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import serializers
from decimal import Decimal

from user_auth_app.models import Profile
from user_auth_app.serializers import (
    UserSerializer, ProfileSerializer, ProfileUpdateSerializer,
    RegistrationSerializer, LoginSerializer
)


class UserSerializerTest(TestCase):
    """Test cases for UserSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_serializer_fields(self):
        """Test UserSerializer field configuration"""
        serializer = UserSerializer(self.user.profile)
        
        expected_fields = ['id', 'username', 'first_name', 'last_name', 'email']
        self.assertEqual(list(serializer.data.keys()), expected_fields)
    
    def test_user_serializer_data(self):
        """Test UserSerializer data output"""
        serializer = UserSerializer(self.user.profile)
        
        self.assertEqual(serializer.data['username'], 'testuser')
        self.assertEqual(serializer.data['first_name'], 'Test')
        self.assertEqual(serializer.data['last_name'], 'User')
        self.assertEqual(serializer.data['email'], 'test@example.com')
        self.assertIsInstance(serializer.data['id'], int)
    
    def test_user_serializer_meta_class(self):
        """Test UserSerializer Meta class configuration"""
        meta = UserSerializer.Meta
        self.assertEqual(meta.model, Profile)
        self.assertEqual(meta.fields, ['id', 'username', 'first_name', 'last_name', 'email'])
        self.assertEqual(meta.read_only_fields, ['id'])


class ProfileSerializerTest(TestCase):
    """Test cases for ProfileSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='testpass123',
            first_name='Profile',
            last_name='User'
        )
        self.profile = self.user.profile
        self.profile.type = 'business'
        self.profile.location = 'Test City'
        self.profile.tel = '+1234567890'
        self.profile.description = 'Test description'
        self.profile.working_hours = '9 AM - 5 PM'
        self.profile.save()
    
    def test_profile_serializer_fields(self):
        """Test ProfileSerializer field configuration"""
        serializer = ProfileSerializer(self.profile)
        
        expected_fields = [
            'user', 'file', 'location', 'tel', 'description', 'working_hours',
            'type', 'created_at', 'username', 'first_name', 'last_name', 'email'
        ]
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))
    
    def test_profile_serializer_data(self):
        """Test ProfileSerializer data output"""
        serializer = ProfileSerializer(self.profile)
        
        # Test read-only fields from user properties
        self.assertEqual(serializer.data['username'], 'profileuser')
        self.assertEqual(serializer.data['first_name'], 'Profile')
        self.assertEqual(serializer.data['last_name'], 'User')
        self.assertEqual(serializer.data['email'], 'profile@example.com')
        
        # Test profile fields
        self.assertEqual(serializer.data['type'], 'business')
        self.assertEqual(serializer.data['location'], 'Test City')
        self.assertEqual(serializer.data['tel'], '+1234567890')
        self.assertEqual(serializer.data['description'], 'Test description')
        self.assertEqual(serializer.data['working_hours'], '9 AM - 5 PM')
        self.assertEqual(serializer.data['user'], self.user.id)
    
    def test_profile_serializer_readonly_fields(self):
        """Test ProfileSerializer read-only field configuration"""
        meta = ProfileSerializer.Meta
        self.assertIn('user', meta.read_only_fields)
        self.assertIn('created_at', meta.read_only_fields)
    
    def test_profile_serializer_readonly_user_properties(self):
        """Test that user property fields are read-only"""
        fields = ProfileSerializer().get_fields()
        
        self.assertTrue(fields['username'].read_only)
        self.assertTrue(fields['first_name'].read_only)
        self.assertTrue(fields['last_name'].read_only)
        self.assertTrue(fields['email'].read_only)
    
    def test_profile_serializer_with_empty_profile(self):
        """Test ProfileSerializer with minimal profile data"""
        empty_user = User.objects.create_user(
            username='empty',
            email='empty@example.com',
            password='pass123'
        )
        
        serializer = ProfileSerializer(empty_user.profile)
        
        self.assertEqual(serializer.data['username'], 'empty')
        self.assertEqual(serializer.data['type'], 'customer')  # Default
        self.assertEqual(serializer.data['location'], '')
        self.assertEqual(serializer.data['tel'], '')
        self.assertEqual(serializer.data['description'], '')
        self.assertEqual(serializer.data['working_hours'], '')


class ProfileUpdateSerializerTest(TestCase):
    """Test cases for ProfileUpdateSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='updateuser',
            email='update@example.com',
            password='testpass123',
            first_name='Original',
            last_name='Name'
        )
        self.profile = self.user.profile
    
    def test_profile_update_serializer_fields(self):
        """Test ProfileUpdateSerializer field configuration"""
        serializer = ProfileUpdateSerializer(self.profile)
        
        expected_fields = [
            'file', 'location', 'tel', 'description', 'working_hours',
            'first_name', 'last_name', 'email'
        ]
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))
    
    def test_profile_update_serializer_meta(self):
        """Test ProfileUpdateSerializer Meta configuration"""
        meta = ProfileUpdateSerializer.Meta
        self.assertEqual(meta.model, Profile)
        
        expected_fields = [
            'file', 'location', 'tel', 'description', 'working_hours',
            'first_name', 'last_name', 'email'
        ]
        self.assertEqual(meta.fields, expected_fields)
    
    def test_user_fields_write_only(self):
        """Test that user fields are write-only"""
        fields = ProfileUpdateSerializer().get_fields()
        
        self.assertTrue(fields['first_name'].write_only)
        self.assertTrue(fields['last_name'].write_only)
        self.assertTrue(fields['email'].write_only)
        self.assertFalse(fields['first_name'].required)
        self.assertFalse(fields['last_name'].required)
        self.assertFalse(fields['email'].required)
    
    def test_update_profile_fields_only(self):
        """Test updating only profile fields"""
        data = {
            'location': 'Updated City',
            'tel': '+9876543210',
            'description': 'Updated description',
            'working_hours': 'Updated hours'
        }
        
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_profile = serializer.save()
        
        self.assertEqual(updated_profile.location, 'Updated City')
        self.assertEqual(updated_profile.tel, '+9876543210')
        self.assertEqual(updated_profile.description, 'Updated description')
        self.assertEqual(updated_profile.working_hours, 'Updated hours')
        
        # User fields should remain unchanged
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Original')
        self.assertEqual(self.user.last_name, 'Name')
    
    def test_update_user_fields_only(self):
        """Test updating only user fields"""
        data = {
            'first_name': 'Updated First',
            'last_name': 'Updated Last',
            'email': 'updated@example.com'
        }
        
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_profile = serializer.save()
        
        # Check user fields were updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated First')
        self.assertEqual(self.user.last_name, 'Updated Last')
        self.assertEqual(self.user.email, 'updated@example.com')
        
        # Profile fields should remain unchanged
        self.assertEqual(updated_profile.location, '')  # Default empty
    
    def test_update_both_profile_and_user_fields(self):
        """Test updating both profile and user fields simultaneously"""
        data = {
            'location': 'Combined City',
            'tel': '+1111111111',
            'first_name': 'Combined First',
            'last_name': 'Combined Last',
            'email': 'combined@example.com'
        }
        
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_profile = serializer.save()
        
        # Check profile fields
        self.assertEqual(updated_profile.location, 'Combined City')
        self.assertEqual(updated_profile.tel, '+1111111111')
        
        # Check user fields
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Combined First')
        self.assertEqual(self.user.last_name, 'Combined Last')
        self.assertEqual(self.user.email, 'combined@example.com')
    
    def test_update_partial_user_fields(self):
        """Test updating some but not all user fields"""
        data = {
            'first_name': 'Partial Update',
            'location': 'Partial City'
        }
        
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        serializer.save()
        
        # Check that only specified fields were updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Partial Update')
        self.assertEqual(self.user.last_name, 'Name')  # Unchanged
        self.assertEqual(self.user.email, 'update@example.com')  # Unchanged
        self.assertEqual(self.profile.location, 'Partial City')
    
    def test_update_invalid_email(self):
        """Test update with invalid email format"""
        data = {
            'email': 'invalid-email-format'
        }
        
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class RegistrationSerializerTest(TestCase):
    """Test cases for RegistrationSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'customer',
            'first_name': 'New',
            'last_name': 'User'
        }
    
    def test_registration_serializer_fields(self):
        """Test RegistrationSerializer field configuration"""
        serializer = RegistrationSerializer(data=self.valid_data)
        
        expected_fields = [
            'username', 'email', 'password', 'repeated_password',
            'type', 'first_name', 'last_name'
        ]
        self.assertEqual(set(serializer.fields.keys()), set(expected_fields))
    
    def test_registration_serializer_meta(self):
        """Test RegistrationSerializer Meta configuration"""
        meta = RegistrationSerializer.Meta
        self.assertEqual(meta.model, User)
        self.assertEqual(meta.fields, [
            'username', 'email', 'password', 'repeated_password',
            'type', 'first_name', 'last_name'
        ])
    
    def test_password_fields_write_only(self):
        """Test that password fields are write-only"""
        fields = RegistrationSerializer().get_fields()
        
        self.assertTrue(fields['password'].write_only)
        self.assertTrue(fields['repeated_password'].write_only)
        self.assertTrue(fields['password'].required)
        self.assertTrue(fields['repeated_password'].required)
    
    def test_valid_registration_data(self):
        """Test serializer with valid registration data"""
        serializer = RegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
    
    def test_password_mismatch_validation(self):
        """Test password mismatch validation"""
        data = self.valid_data.copy()
        data['repeated_password'] = 'differentpassword'
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Passwords do not match', str(serializer.errors))
    
    def test_duplicate_email_validation(self):
        """Test duplicate email validation"""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123'
        )
        
        data = self.valid_data.copy()
        data['email'] = 'existing@example.com'
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('Email already exists', str(serializer.errors))
    
    def test_invalid_user_type(self):
        """Test invalid user type validation"""
        data = self.valid_data.copy()
        data['type'] = 'invalid_type'
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('type', serializer.errors)
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields"""
        # Test missing username
        data = self.valid_data.copy()
        del data['username']
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
        
        # Test missing password
        data = self.valid_data.copy()
        del data['password']
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        
        # Test missing type
        data = self.valid_data.copy()
        del data['type']
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('type', serializer.errors)
    
    def test_optional_fields(self):
        """Test that first_name and last_name are optional"""
        data = {
            'username': 'minimaluser',
            'email': 'minimal@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'customer'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_create_user_business_type(self):
        """Test creating user with business type"""
        data = self.valid_data.copy()
        data['type'] = 'business'
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        # Verify user creation
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('securepass123'))
        
        # Verify profile type
        self.assertEqual(user.profile.type, 'business')
    
    def test_create_user_customer_type(self):
        """Test creating user with customer type"""
        serializer = RegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        self.assertEqual(user.profile.type, 'customer')
    
    def test_create_user_without_optional_names(self):
        """Test creating user without first_name and last_name"""
        data = {
            'username': 'nonames',
            'email': 'nonames@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'customer'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
    
    def test_repeated_password_not_saved(self):
        """Test that repeated_password is not saved to user"""
        serializer = RegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        # Check that repeated_password is removed from validated_data during save
        user = serializer.save()
        
        # User should only have the main password, not repeated_password
        self.assertTrue(hasattr(user, 'password'))
        # repeated_password should not be an attribute on the created user
        self.assertFalse(hasattr(user, 'repeated_password'))


class LoginSerializerTest(TestCase):
    """Test cases for LoginSerializer"""
    
    def test_login_serializer_fields(self):
        """Test LoginSerializer field configuration"""
        serializer = LoginSerializer()
        
        expected_fields = ['username', 'password']
        self.assertEqual(list(serializer.fields.keys()), expected_fields)
    
    def test_username_field_configuration(self):
        """Test username field configuration"""
        fields = LoginSerializer().get_fields()
        
        username_field = fields['username']
        self.assertEqual(username_field.max_length, 150)
        self.assertFalse(username_field.write_only)
    
    def test_password_field_configuration(self):
        """Test password field configuration"""
        fields = LoginSerializer().get_fields()
        
        password_field = fields['password']
        self.assertEqual(password_field.max_length, 128)
        self.assertTrue(password_field.write_only)
        self.assertEqual(password_field.style['input_type'], 'password')
    
    def test_valid_login_data(self):
        """Test serializer with valid login data"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['username'], 'testuser')
        self.assertEqual(serializer.validated_data['password'], 'testpass123')
    
    def test_missing_username(self):
        """Test validation with missing username"""
        data = {
            'password': 'testpass123'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
    
    def test_missing_password(self):
        """Test validation with missing password"""
        data = {
            'username': 'testuser'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_empty_fields(self):
        """Test validation with empty fields"""
        data = {
            'username': '',
            'password': ''
        }
        
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
        self.assertIn('password', serializer.errors)
    
    def test_email_as_username(self):
        """Test that email can be used as username field"""
        data = {
            'username': 'user@example.com',
            'password': 'testpass123'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['username'], 'user@example.com')
    
    def test_long_username(self):
        """Test username length validation"""
        data = {
            'username': 'x' * 151,  # Exceeds max_length of 150
            'password': 'testpass123'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
    
    def test_long_password(self):
        """Test password length validation"""
        data = {
            'username': 'testuser',
            'password': 'x' * 129  # Exceeds max_length of 128
        }
        
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class SerializerIntegrationTest(TestCase):
    """Integration tests for serializers"""
    
    def test_profile_serialization_flow(self):
        """Test complete profile serialization workflow"""
        # Create user through RegistrationSerializer
        registration_data = {
            'username': 'flowuser',
            'email': 'flow@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'business',
            'first_name': 'Flow',
            'last_name': 'User'
        }
        
        reg_serializer = RegistrationSerializer(data=registration_data)
        self.assertTrue(reg_serializer.is_valid())
        user = reg_serializer.save()
        
        # Serialize profile with ProfileSerializer
        profile_serializer = ProfileSerializer(user.profile)
        profile_data = profile_serializer.data
        
        self.assertEqual(profile_data['username'], 'flowuser')
        self.assertEqual(profile_data['type'], 'business')
        self.assertEqual(profile_data['first_name'], 'Flow')
        self.assertEqual(profile_data['last_name'], 'User')
        self.assertEqual(profile_data['email'], 'flow@example.com')
        
        # Update profile with ProfileUpdateSerializer
        update_data = {
            'location': 'Flow City',
            'description': 'Flow description',
            'first_name': 'Updated Flow'
        }
        
        update_serializer = ProfileUpdateSerializer(
            user.profile, 
            data=update_data, 
            partial=True
        )
        self.assertTrue(update_serializer.is_valid())
        updated_profile = update_serializer.save()
        
        # Verify updates
        user.refresh_from_db()
        self.assertEqual(updated_profile.location, 'Flow City')
        self.assertEqual(updated_profile.description, 'Flow description')
        self.assertEqual(user.first_name, 'Updated Flow')
        self.assertEqual(user.last_name, 'User')  # Unchanged
    
    def test_serializer_error_handling(self):
        """Test error handling across different serializers"""
        # Test registration with conflicting data
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123'
        )
        
        # Try to register with existing email
        reg_data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'pass123',
            'repeated_password': 'different',  # Also password mismatch
            'type': 'invalid'  # Also invalid type
        }
        
        reg_serializer = RegistrationSerializer(data=reg_data)
        self.assertFalse(reg_serializer.is_valid())
        
        # Should have multiple errors
        self.assertIn('email', reg_serializer.errors)
        self.assertIn('type', reg_serializer.errors)
        # Password mismatch is in non_field_errors
        self.assertTrue(any('Passwords do not match' in str(error) 
                            for error in reg_serializer.errors.values()))