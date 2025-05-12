from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for Django's User model.
    
    Ensures that the password is only used for writing and is securely stored.
    """
    userID = serializers.IntegerField(source='id', read_only=True)
    name = serializers.CharField(source='username')
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        """
        Creates a new user.
        
        Uses Django's create_user method to ensure secure password hashing.
        
        Args:
            validated_data: Dict with validated data for creating the user
            
        Returns:
            User: Newly created User object with securely stored password
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data.get('password', '')
        )
        return user