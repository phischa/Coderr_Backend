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

class ProfileViewSet(viewsets.ModelViewSet):
    """API endpoint for user profiles"""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ProfileUpdateSerializer
        return ProfileSerializer

    @action(detail=True, methods=['GET', 'PATCH'], url_path='by-user')
    def get_by_user_id(self, request, pk=None):
        """Get profile by user ID instead of profile ID"""
        profile = get_object_or_404(Profile, user_id=pk)
    
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
    
        elif request.method == 'PATCH':
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
        profile.type = 'customer'  # Default guest to customer type
        profile.save()
        
        token, _ = Token.objects.get_or_create(user=guest_user)
        
        return Response({
            'status': 'success',
            'token': token.key,
            'user_id': guest_user.id,
            'username': guest_username,
            'is_guest': True
        })