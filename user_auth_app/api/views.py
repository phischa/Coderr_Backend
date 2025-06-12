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
from user_auth_app.api.permissions import IsProfileOwner  # Import custom permission
from .serializers import (
    UserSerializer, ProfileSerializer, ProfileUpdateSerializer,
    RegistrationSerializer, LoginSerializer, CustomerProfileSerializer, 
    BusinessProfileSerializer
)


GUEST_CREDENTIALS = {
    'customer': {
        'username': 'andrey',
        'password': 'asdasd'
    },
    'business': {
        'username': 'kevin',
        'password': 'asdasd24'
    }
}


@api_view(['POST'])
def login_view(request):
    """
    Unified login handler for both regular users and guest users.
    
    Detects guest login attempts based on predefined credentials and
    creates/retrieves session-based guest users automatically.
    
    Args:
        request: Contains username/email and password
        
    Returns:
        Response with token and user info or error message
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        guest_type = None
        for user_type, credentials in GUEST_CREDENTIALS.items():
            if username == credentials['username'] and password == credentials['password']:
                guest_type = user_type
                break
        
        if guest_type:
            return handle_guest_login(request, guest_type)
        else:
            user = authenticate(username=username, password=password)
            
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key,
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'type': user.profile.type,
                    'is_guest': user.profile.is_guest
                })
            
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def handle_guest_login(request, guest_type):
    """
    Handle guest login by creating or retrieving a session-based guest user.
    
    Args:
        request: The HTTP request
        guest_type: Either 'customer' or 'business'
        
    Returns:
        Response with guest user token and info
    """
    # Check if there's already a guest user in the session
    session_key = f'guest_{guest_type}_user_id'
    existing_guest_id = request.session.get(session_key)
    
    if existing_guest_id:
        try:
            guest_user = User.objects.get(id=existing_guest_id, profile__is_guest=True)
            token, _ = Token.objects.get_or_create(user=guest_user)
            
            return Response({
                'token': token.key,
                'user_id': guest_user.id,
                'username': guest_user.username,
                'email': guest_user.email,  
                'type': guest_type,
                'is_guest': True,
                'message': 'Existing guest session retrieved'
            })
        except User.DoesNotExist:
            pass

    guest_username = f"guest_{guest_type}_{uuid.uuid4().hex[:8]}"
    temp_password = uuid.uuid4().hex
    
    guest_user = User.objects.create_user(
        username=guest_username,
        email=f"{guest_username}@example.com",
        password=temp_password
    )
    profile = guest_user.profile
    profile.is_guest = True
    profile.type = guest_type
    profile.save()
    token, _ = Token.objects.get_or_create(user=guest_user)
    request.session[session_key] = guest_user.id
    request.session.set_expiry(86400)  # Session expires after 24 hours
    
    return Response({
        'token': token.key,
        'user_id': guest_user.id,
        'username': guest_username,
        'email': guest_user.email,  # Fixed typo: was 'guest.email'
        'type': guest_type,
        'is_guest': True,
        'message': 'New guest user created'
    })


@api_view(['POST'])
def registration_view(request):
    """
    Handle user registration.
    Creates the user, profile, and returns the auth token.
    
    Args:
        request: Contains user registration data including type
        
    Returns:
        Response with token and user info or error message
    """
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        profile_type = serializer.validated_data.get('type')
        profile = user.profile
        profile.type = profile_type
        profile.save()
        
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'type': profile_type,
            'is_guest': False
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user profiles.
    Provides CRUD operations for user profiles with proper permission checks.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsProfileOwner]  # Added IsProfileOwner
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['update', 'partial_update']:
            return ProfileUpdateSerializer
        return ProfileSerializer

    def get_object(self):
        """
        Override to get profile by user_id when pk represents user_id.
        This ensures the API works with user IDs as documented.
        """
        pk = self.kwargs.get('pk')
        
        # For profile-specific endpoints, pk is the user_id
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return get_object_or_404(Profile, user_id=pk)
        
        return super().get_object()

    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/profile/{pk}/ - Get profile by user ID
        
        Returns profile data with all fields as non-null strings
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/profile/{pk}/ - Update profile by user ID
        
        Enforces ownership check and returns proper status codes:
        - 200: Success
        - 401: Not authenticated
        - 403: Not the owner of the profile
        - 404: Profile not found
        """
        instance = self.get_object()
        
        # Check ownership (this is also done by IsProfileOwner permission)
        # but we want to be explicit about guest users
        if request.user.profile.is_guest:
            return Response(
                {'error': 'Guest users cannot update profiles'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # The permission class handles the ownership check
        # but we can add an explicit check if needed
        if instance.user != request.user:
            return Response(
                {'error': 'You can only update your own profile'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            # Return the full profile data after update
            response_serializer = ProfileSerializer(instance)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'], url_path='business')
    def business_profiles(self, request):
        """
        List all business profiles.
        
        Returns:
            List of business profiles with all fields as non-null strings
        """
        profiles = Profile.objects.filter(type='business')
        serializer = BusinessProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'], url_path='customer')
    def customer_profiles(self, request):
        """
        List all customer profiles.
        
        Returns:
            List of customer profiles with all fields as non-null strings
        """
        profiles = Profile.objects.filter(type='customer')
        serializer = CustomerProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['GET', 'PATCH'], url_path='by-user')
    def get_by_user_id(self, request, pk=None):
        """
        Alternative endpoint: Get/update profile by user ID.
        Kept for backward compatibility.
        
        Args:
            request: HTTP request
            pk: User ID
            
        Returns:
            Profile data for the specified user
        """
        profile = get_object_or_404(Profile, user_id=pk)
    
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
    
        elif request.method == 'PATCH':
            if request.user.id != pk or request.user.profile.is_guest:
                return Response(
                    {'error': 'You can only update your own profile. Guest users cannot update profiles.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Return full profile data
                response_serializer = ProfileSerializer(profile)
                return Response(response_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
