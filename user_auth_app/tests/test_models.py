from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from user_auth_app.models import Profile


class ProfileModelTest(TestCase):
    """Test cases for Profile model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_profile_creation_signal(self):
        """Test that Profile is automatically created when User is created"""
        # Profile should be created automatically via signal
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, Profile)
        self.assertEqual(self.user.profile.type, 'customer')  # Default type
    
    def test_profile_str_representation(self):
        """Test Profile string representation"""
        expected = f"{self.user.username} ({self.user.profile.type})"
        self.assertEqual(str(self.user.profile), expected)
    
    def test_profile_user_types_choices(self):
        """Test Profile USER_TYPES choices"""
        expected_choices = [('business', 'Business'), ('customer', 'Customer')]
        self.assertEqual(Profile.USER_TYPES, expected_choices)
    
    def test_profile_default_values(self):
        """Test Profile default field values"""
        profile = self.user.profile
        self.assertEqual(profile.type, 'customer')
        self.assertFalse(profile.is_guest)
        self.assertEqual(profile.location, '')
        self.assertEqual(profile.tel, '')
        self.assertEqual(profile.description, '')
        self.assertEqual(profile.working_hours, '')
        self.assertIsNone(profile.file.name if profile.file else None)
    
    def test_profile_properties(self):
        """Test Profile property methods"""
        profile = self.user.profile
        
        self.assertEqual(profile.username, self.user.username)
        self.assertEqual(profile.first_name, self.user.first_name)
        self.assertEqual(profile.last_name, self.user.last_name)
        self.assertEqual(profile.email, self.user.email)
    
    def test_profile_business_type(self):
        """Test Profile with business type"""
        profile = self.user.profile
        profile.type = 'business'
        profile.save()
        
        self.assertEqual(profile.type, 'business')
        self.assertEqual(str(profile), f"{self.user.username} (business)")
    
    def test_profile_guest_user(self):
        """Test Profile with guest user"""
        profile = self.user.profile
        profile.is_guest = True
        profile.save()
        
        self.assertTrue(profile.is_guest)
    
    def test_profile_with_all_fields(self):
        """Test Profile with all optional fields filled"""
        profile = self.user.profile
        profile.location = 'Test City'
        profile.tel = '+1234567890'
        profile.description = 'Test description'
        profile.working_hours = '9 AM - 5 PM'
        profile.type = 'business'
        profile.is_guest = False
        profile.save()
        
        profile.refresh_from_db()
        self.assertEqual(profile.location, 'Test City')
        self.assertEqual(profile.tel, '+1234567890')
        self.assertEqual(profile.description, 'Test description')
        self.assertEqual(profile.working_hours, '9 AM - 5 PM')
        self.assertEqual(profile.type, 'business')
        self.assertFalse(profile.is_guest)
    
    def test_profile_ordering(self):
        """Test Profile Meta ordering"""
        # Create additional users to test ordering
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='pass123'
        )
        
        profiles = Profile.objects.all()
        # Should be ordered by id (first created first)
        self.assertEqual(profiles[0], self.user.profile)
        self.assertEqual(profiles[1], user2.profile)
        self.assertEqual(profiles[2], user3.profile)
    
    def test_one_to_one_relationship(self):
        """Test OneToOneField relationship integrity"""
        # Each user should have exactly one profile
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)
        
        # Attempting to create another profile for same user should fail
        with self.assertRaises(IntegrityError):
            Profile.objects.create(user=self.user, type='business')


class ProfileSignalTest(TestCase):
    """Test cases for Profile signals"""
    
    def test_create_user_profile_signal(self):
        """Test create_user_profile signal"""
        # Profile should not exist before user creation
        self.assertEqual(Profile.objects.count(), 0)
        
        # Create user
        user = User.objects.create_user(
            username='signaltest',
            email='signal@test.com',
            password='testpass'
        )
        
        # Profile should be created automatically
        self.assertEqual(Profile.objects.count(), 1)
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.type, 'customer')
    
    def test_save_user_profile_signal(self):
        """Test save_user_profile signal"""
        user = User.objects.create_user(
            username='savetest',
            email='save@test.com',
            password='testpass'
        )
        
        original_profile = user.profile
        
        # Modify user (this should trigger save_user_profile signal)
        user.first_name = 'Updated'
        user.save()
        
        # Profile should still exist and be the same instance
        user.refresh_from_db()
        self.assertEqual(user.profile.id, original_profile.id)
    
    def test_signal_with_existing_user_update(self):
        """Test signals when updating existing user"""
        user = User.objects.create_user(
            username='updatetest',
            email='update@test.com',
            password='testpass'
        )
        
        profile_count_before = Profile.objects.count()
        
        # Update user info
        user.email = 'newemail@test.com'
        user.first_name = 'New Name'
        user.save()
        
        # Should not create additional profiles
        self.assertEqual(Profile.objects.count(), profile_count_before)
        
        # Profile should reflect updated user info through properties
        user.refresh_from_db()
        self.assertEqual(user.profile.email, 'newemail@test.com')
        self.assertEqual(user.profile.first_name, 'New Name')


class ProfileModelEdgeCasesTest(TestCase):
    """Test edge cases and error conditions for Profile model"""
    
    def test_profile_with_empty_user_fields(self):
        """Test Profile when user has empty fields"""
        user = User.objects.create_user(
            username='emptyuser',
            email='',  # Empty email
            password='testpass'
        )
        
        profile = user.profile
        self.assertEqual(profile.email, '')
        self.assertEqual(profile.first_name, '')
        self.assertEqual(profile.last_name, '')
    
    def test_profile_with_very_long_fields(self):
        """Test Profile with maximum length fields"""
        user = User.objects.create_user(
            username='longuser',
            email='long@test.com',
            password='testpass'
        )
        
        profile = user.profile
        # Test CharField max_length constraints
        profile.location = 'x' * 255  # Max length for location
        profile.tel = '1' * 20  # Max length for tel
        profile.working_hours = 'x' * 255  # Max length for working_hours
        profile.description = 'x' * 1000  # TextField can be very long
        
        try:
            profile.full_clean()  # This validates field constraints
            profile.save()
        except Exception as e:
            self.fail(f"Profile with max length fields should be valid: {e}")
    
    def test_profile_invalid_type_choice(self):
        """Test Profile with invalid type choice"""
        user = User.objects.create_user(
            username='invaliduser',
            email='invalid@test.com',
            password='testpass'
        )
        
        profile = user.profile
        profile.type = 'invalid_type'
        
        # Should raise ValidationError during full_clean
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            profile.full_clean()
    
    def test_profile_meta_attributes(self):
        """Test Profile Meta class attributes"""
        meta = Profile._meta
        self.assertEqual(meta.ordering, ['id'])
        
        # Test verbose names if defined
        self.assertEqual(meta.object_name, 'Profile')
    
    def test_profile_field_attributes(self):
        """Test Profile field attributes and constraints"""
        # Test OneToOneField
        user_field = Profile._meta.get_field('user')
        self.assertEqual(user_field.related_model, User)
        self.assertEqual(user_field.on_delete.__name__, 'CASCADE')
        self.assertEqual(user_field.related_query_name(), 'profile')
        
        # Test CharField constraints
        location_field = Profile._meta.get_field('location')
        self.assertEqual(location_field.max_length, 255)
        self.assertTrue(location_field.blank)
        
        tel_field = Profile._meta.get_field('tel')
        self.assertEqual(tel_field.max_length, 20)
        self.assertTrue(tel_field.blank)
        
        # Test TextField
        description_field = Profile._meta.get_field('description')
        self.assertTrue(description_field.blank)
        
        # Test ImageField
        file_field = Profile._meta.get_field('file')
        self.assertEqual(file_field.upload_to, 'profile-images/')
        self.assertTrue(file_field.null)
        self.assertTrue(file_field.blank)
        
        # Test BooleanField
        is_guest_field = Profile._meta.get_field('is_guest')
        self.assertFalse(is_guest_field.default)
        
        # Test DateTimeField
        created_at_field = Profile._meta.get_field('created_at')
        self.assertTrue(created_at_field.auto_now_add)
        