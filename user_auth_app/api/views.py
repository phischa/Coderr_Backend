
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
import uuid

from user_auth_app.models import Profile
from .serializers import (
    UserSerializer, ProfileSerializer, ProfileUpdateSerializer,
    RegistrationSerializer, LoginSerializer
)


@api_view(['POST'])
def login_view(request):
    """Handle user login and return auth token"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username
            })
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def registration_view(request):
    """Handle user registration"""
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileList(generics.ListCreateAPIView):
    """
    API view for listing all user profiles or creating a new one.
    
    Provides GET (list all profiles) and POST (create profile) functionality.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    """API endpoint for user profiles"""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ProfileUpdateSerializer
        return ProfileSerializer
    
    @action(detail=False, methods=['GET'], url_path='business')
    def business_profiles(self, request):
        """List all business profiles"""
        profiles = Profile.objects.filter(type='business')
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'], url_path='customer')
    def customer_profiles(self, request):
        """List all customer profiles"""
        profiles = Profile.objects.filter(type='customer')
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)

class RegistrationView(APIView):
    """
    API view for user registration.
    
    Handles user creation with validation for passwords and email uniqueness.
    Returns an authentication token upon successful registration.
    Accessible to unauthenticated users.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Process a registration request.
        
        Validates user data, creates a new user, and returns an auth token.
        Formats validation errors in a frontend-friendly structure.
        
        Args:
            request: The HTTP request containing registration data.
            
        Returns:
            Response: Success response with token, username, email, and userID,
            or error response with validation details.
        """
        serializer = RegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                saved_account = serializer.save()
                token, created = Token.objects.get_or_create(user=saved_account)
                return Response({
                    'status': 'success',
                    'token': token.key,
                    'username': saved_account.username,
                    'email': saved_account.email,
                    'userID': saved_account.id  # ID zurückgeben für Frontend
                })
            except Exception as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
        else:
            # Formatierter Fehler mit flacher Struktur für einfachere Frontend-Verarbeitung
            errors = {}
            for field, error_msgs in serializer.errors.items():
                errors[field] = error_msgs[0] if error_msgs else "Invalid data"
            
            return Response({
                'status': 'error',
                'errors': errors
            }, status=400)
    
class CustomLoginView(ObtainAuthToken):
    """
    Custom login view that extends Django REST framework's ObtainAuthToken.
    
    Provides token-based authentication with a simplified response structure.
    Accessible to unauthenticated users.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Process a login request.
        
        Validates credentials and returns user information with an auth token.
        
        Args:
            request: The HTTP request containing login credentials.
            
        Returns:
            Response: User information and token on success,
            or validation errors on failure.
        """
        serializer = self.serializer_class(data=request.data)
        data = {}

        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            data = {
                'token': token.key,
                'username': user.username,
                'email': user.email
            }
        else: 
            data = serializer.errors
        return Response(data)

class GuestLoginView(APIView):
    """
    API view for guest user login.
    
    Creates a temporary user account with a unique username and random password.
    Returns an authentication token for the guest user.
    Accessible to unauthenticated users.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Process a guest login request.
        
        Creates a temporary user with a UUID-based username and random password.
        Marks the user profile as a guest account.
        
        Args:
            request: The HTTP request object.
            
        Returns:
            Response: Success response with token, username, email,
            and guest status flag.
        """
        guest_username = f"guest_{uuid.uuid4().hex[:8]}"
        temp_password = uuid.uuid4().hex
        guest_user = User.objects.create_user(
            username = guest_username,
            email = f"{guest_username}@example.com",
            password = temp_password
        )
        profile = guest_user.profile
        profile.is_guest = True
        profile.save()
        
        token, _ = Token.objects.get_or_create(user=guest_user)
        
        return Response({
            'status': 'success',
            'token': token.key,
            'username': guest_username,
            'email': f"{guest_username}@example.com",
            'is_guest': True
        })