from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import serializers
from user_auth_app.models import Profile
from user_auth_app.api.serializers import (
    UserSerializer, ProfileSerializer, ProfileUpdateSerializer,
    RegistrationSerializer, LoginSerializer
)


class UserSerializerTest(TestCase):
    """Test cases for UserSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.profile = self.user.profile

    def test_user_serializer_fields(self):
        """Test that UserSerializer returns correct fields"""
        serializer = UserSerializer(instance=self.profile)
        data = serializer.data
        
        expected_fields = {'id', 'username', 'first_name', 'last_name', 'email'}
        self.assertEqual(set(data.keys()), expected_fields)
        
    def test_user_serializer_data(self):
        """Test that UserSerializer returns correct data"""
        serializer = UserSerializer(instance=self.profile)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')

    def test_user_serializer_read_only_id(self):
        """Test that id field is read-only"""
        serializer = UserSerializer()
        self.assertIn('id', serializer.Meta.read_only_fields)


class ProfileSerializerTest(TestCase):
    """Test cases for ProfileSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.profile = self.user.profile
        self.profile.location = 'Test Location'
        self.profile.tel = '+1234567890'
        self.profile.description = 'Test Description'
        self.profile.working_hours = '9-5'
        self.profile.type = 'business'
        self.profile.save()

    def test_profile_serializer_fields(self):
        """Test that ProfileSerializer includes all expected fields"""
        serializer = ProfileSerializer(instance=self.profile)
        data = serializer.data
        
        expected_fields = {
            'user', 'file', 'location', 'tel', 'description', 
            'working_hours', 'type', 'created_at', 'username', 
            'first_name', 'last_name', 'email'
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_profile_serializer_user_fields(self):
        """Test that user fields are correctly included"""
        serializer = ProfileSerializer(instance=self.profile)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['email'], 'test@example.com')

    def test_profile_serializer_profile_fields(self):
        """Test that profile fields are correctly serialized"""
        serializer = ProfileSerializer(instance=self.profile)
        data = serializer.data
        
        self.assertEqual(data['location'], 'Test Location')
        self.assertEqual(data['tel'], '+1234567890')
        self.assertEqual(data['description'], 'Test Description')
        self.assertEqual(data['working_hours'], '9-5')
        self.assertEqual(data['type'], 'business')

    def test_profile_serializer_read_only_fields(self):
        """Test that certain fields are read-only"""
        serializer = ProfileSerializer()
        read_only_fields = serializer.Meta.read_only_fields
        
        expected_read_only = {'user', 'created_at'}
        self.assertTrue(expected_read_only.issubset(set(read_only_fields)))


class ProfileUpdateSerializerTest(TestCase):
    """Test cases for ProfileUpdateSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Original',
            last_name='Name'
        )
        self.profile = self.user.profile

    def test_profile_update_serializer_fields(self):
        """Test that ProfileUpdateSerializer includes correct fields"""
        serializer = ProfileUpdateSerializer()
        expected_fields = {
            'file', 'location', 'tel', 'description', 
            'working_hours', 'first_name', 'last_name', 'email'
        }
        self.assertEqual(set(serializer.Meta.fields), expected_fields)

    def test_update_user_fields(self):
        """Test updating user fields through ProfileUpdateSerializer"""
        data = {
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'updated@example.com',
            'location': 'New Location'
        }
        
        serializer = ProfileUpdateSerializer(instance=self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_profile = serializer.save()
        self.user.refresh_from_db()
        
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(updated_profile.location, 'New Location')

    def test_partial_update(self):
        """Test partial update functionality"""
        data = {'location': 'Partial Update Location'}
        
        serializer = ProfileUpdateSerializer(instance=self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_profile = serializer.save()
        self.assertEqual(updated_profile.location, 'Partial Update Location')


class RegistrationSerializerTest(TestCase):
    """Test cases for RegistrationSerializer"""
    
    def test_valid_registration_data(self):
        """Test registration with valid data"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpassword123',
            'repeated_password': 'testpassword123',
            'type': 'customer',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        """Test validation fails when passwords don't match"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpassword123',
            'repeated_password': 'differentpassword',
            'type': 'customer'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Passwords do not match', str(serializer.errors))

    def test_duplicate_email(self):
        """Test validation fails for duplicate email"""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password'
        )
        
        data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'testpassword123',
            'repeated_password': 'testpassword123',
            'type': 'customer'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_create_user_with_profile(self):
        """Test that create method creates user and sets profile type"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpassword123',
            'repeated_password': 'testpassword123',
            'type': 'business',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.profile.type, 'business')

    def test_required_fields_safe(self):
        """Test required fields validation - safe version"""
        serializer = RegistrationSerializer(data={})
        self.assertFalse(serializer.is_valid())
        
        # Check only core fields that definitely should be required
        core_required_fields = {'username', 'password', 'repeated_password', 'type'}
        error_fields = set(serializer.errors.keys())
        
        for field in core_required_fields:
            self.assertIn(field, error_fields, f"Field '{field}' should be required")


class LoginSerializerTest(TestCase):
    """Test cases for LoginSerializer"""
    
    def test_valid_login_data(self):
        """Test login serializer with valid data"""
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        self.assertEqual(serializer.validated_data['username'], 'testuser')
        self.assertEqual(serializer.validated_data['password'], 'testpassword')

    def test_missing_fields(self):
        """Test login serializer with missing fields"""
        # Missing password
        serializer = LoginSerializer(data={'username': 'testuser'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        
        # Missing username
        serializer = LoginSerializer(data={'password': 'testpassword'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_password_write_only(self):
        """Test that password field is write-only"""
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Password should not appear in serialized data
        self.assertNotIn('password', serializer.data)
        