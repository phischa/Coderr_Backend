from rest_framework import serializers
from django.contrib.auth.models import User
from user_auth_app.models import Profile


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    class Meta:
        model = Profile
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']

class ProfileSerialiszer(serializers.ModelSerializer):
    """
    Serializer for the Profile model.
    Includes user data through nested serializer.
    """
    username = serializers.ReadOnlyField()
    first_name = serializers.ReadOnlyField()
    last_name = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    
    class Meta:
        model = Profile
        fields = ['user', 'file', 'location', 'tel', 'description', 'working_hours', 
                    'type', 'created_at', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['user', 'created_at']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Profile objects.
    Allows updating both User and Profile fields.
    """
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = Profile
        fields = ['file', 'location', 'tel', 'description', 'working_hours', 
                    'first_name', 'last_name', 'email']

class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Handles the creation of new User objects with proper password validation.
    Includes validation to ensure password confirmation matches and
    that the email is not already in use.
    """
    repeated_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'repeated_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }
    
    def save(self):
        """
        Creates and saves a new User.
        
        Validates that passwords match and the email is unique
        before creating the user with a securely hashed password.
        
        Returns:
            User: The newly created User object.
            
        Raises:
            ValidationError: If passwords don't match or email already exists.
        """
        pw = self.validated_data['password']
        repeated_pw = self.validated_data['repeated_password']
        email = self.validated_data['email']

        if pw != repeated_pw:
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Email already exists'})
        
        account = User(email=email, username=self.validated_data['username'])
        account.set_password(pw)
        account.save()
        return account
