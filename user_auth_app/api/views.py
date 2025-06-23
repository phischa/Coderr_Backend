from django.shortcuts import get_object_or_404
from django.http import Http404
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
from user_auth_app.api.permissions import IsProfileOwner
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
    Documentation-compliant login handler.
    Returns the documented fields: token, username, email, user_id
    Status Codes: 200, 400, 500
    """
    try:
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            # Check for guest login
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
                    # CORRECTED: Only return documented fields
                    return Response({
                        'token': token.key,
                        'username': user.username,
                        'email': user.email,
                        'user_id': user.id
                    }, status=status.HTTP_200_OK)
                
                return Response({'error': 'Ungültige Anfragedaten'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'error': 'Ungültige Anfragedaten'}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({'error': 'Interner Serverfehler'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_guest_login(request, guest_type):
    """
    Handle guest login with documentation-compliant response.
    """
    try:
        # Check if there's already a guest user in the session
        session_key = f'guest_{guest_type}_user_id'
        existing_guest_id = request.session.get(session_key)
        
        if existing_guest_id:
            try:
                guest_user = User.objects.get(id=existing_guest_id, profile__is_guest=True)
                token, _ = Token.objects.get_or_create(user=guest_user)
                
                # CORRECTED: Only return documented fields
                return Response({
                    'token': token.key,
                    'username': guest_user.username,
                    'email': guest_user.email,
                    'user_id': guest_user.id
                }, status=status.HTTP_200_OK)
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
        
        # CORRECTED: Only return documented fields
        return Response({
            'token': token.key,
            'username': guest_username,
            'email': guest_user.email,
            'user_id': guest_user.id
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': 'Interner Serverfehler'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def registration_view(request):
    """
    Documentation-compliant registration handler.
    
    Returns the documented fields: token, username, email, user_id
    Status Codes: 201, 400, 500
    """
    try:
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            
            # CORRECTED: Return 201 status and only documented fields
            return Response({
                'token': token.key,
                'username': user.username,
                'email': user.email,
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        
        return Response({'error': 'Ungültige Anfragedaten'}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({'error': 'Interner Serverfehler'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileViewSet(viewsets.ModelViewSet):
    """
    Documentation-compliant API endpoint for user profiles.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsProfileOwner]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['update', 'partial_update']:
            return ProfileUpdateSerializer
        return ProfileSerializer

    def get_object(self):
        """
        Override to get profile by user_id when pk represents user_id.
        """
        pk = self.kwargs.get('pk')
        
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return get_object_or_404(Profile, user_id=pk)
        
        return super().get_object()

    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/profile/{pk}/ - Get profile by user ID
        Status Codes: 200, 401, 404, 500
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Http404:
            return Response(
                {'error': 'Das Benutzerprofil wurde nicht gefunden'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/profile/{pk}/ - Update profile by user ID
        Status Codes: 200, 401, 403, 404, 500
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            try:
                instance = self.get_object()

            except Http404:
                return Response(
                    {'error': 'Das Benutzerprofil wurde nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check ownership
            if instance.user != request.user:
                return Response(
                    {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer Profils'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Guest users cannot update profiles
            if request.user.profile.is_guest:
                return Response(
                    {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer Profils'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                self.perform_update(serializer)
                # Return the full profile data after update
                response_serializer = ProfileSerializer(instance)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            
            return Response({'error': 'Ungültige Anfragedaten'}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'], url_path='business')
    def business_profiles(self, request):
        """
        GET /api/profiles/business/ - List all business profiles
        Status Codes: 200, 401, 500
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            profiles = Profile.objects.filter(type='business')
            serializer = BusinessProfileSerializer(profiles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'], url_path='customer')
    def customer_profiles(self, request):
        """
        GET /api/profiles/customer/ - List all customer profiles
        Status Codes: 200, 401, 500
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            profiles = Profile.objects.filter(type='customer')
            serializer = CustomerProfileSerializer(profiles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['GET', 'PATCH'], url_path='by-user')
    def get_by_user_id(self, request, pk=None):
        """
        Alternative endpoint: Get/update profile by user ID.
        Kept for backward compatibility.
        """
        try:
            profile = get_object_or_404(Profile, user_id=pk)
        
            if request.method == 'GET':
                if not request.user.is_authenticated:
                    return Response(
                        {'error': 'Benutzer ist nicht authentifiziert'}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                serializer = self.get_serializer(profile)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
            elif request.method == 'PATCH':
                if not request.user.is_authenticated:
                    return Response(
                        {'error': 'Benutzer ist nicht authentifiziert'}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
                if request.user.id != int(pk) or request.user.profile.is_guest:
                    return Response(
                        {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer Profils'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    # Return full profile data
                    response_serializer = ProfileSerializer(profile)
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                return Response({'error': 'Ungültige Anfragedaten'}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )