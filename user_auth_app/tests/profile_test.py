from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from user_auth_app.models import Profile
from user_auth_app.serializers import (
    UserSerializer, ProfileSerializer, 
    ProfileUpdateSerializer, RegistrationSerializer
)

class ProfileTests(APITestCase):
    """
    Test case for the Profile model.
    """
    def setUp(self):
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