from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth.models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing User objects.
    
    Provides CRUD operations for users.
    Regular users can only see and modify their own user,
    while staff users can access all users.
    """
    serializer_class = UserSerializer
    
    def get_queryset(self):
        """
        Returns users filtered by permissions.
        
        Staff users see all users, while regular users only see themselves.
        
        Returns:
            QuerySet: User objects based on permission,
            or an empty QuerySet if not authenticated.
        """
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return User.objects.all()
            return User.objects.filter(id=user.id)
        return User.objects.none()
    
    def get_serializer(self, *args, **kwargs):
        """
        Handle both single item and list serialization.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Returns:
            Serializer: The appropriate serializer instance.
        """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)
    
    def list(self, request):
        """
        Lists users based on permissions.
        
        Args:
            request: The HTTP request.
            
        Returns:
            Response: Serialized users data.
        """
        users = self.get_queryset()
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """
        Creates a new user.
        
        This is primarily for admin functionality.
        Regular user registration should normally use a dedicated registration view.
        
        Args:
            request: The HTTP request containing user data.
            
        Returns:
            Response: Success message if created, or validation errors.
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def hello_world(request):
    """
    A simple API view that returns a hello message.
    
    Args:
        request: The HTTP request.
        
    Returns:
        Response: A JSON response with a "Hello World!" message.
    """
    return Response({"message": "Hello World!"})