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

class ProfileSerializer(serializers.ModelSerializer):
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
    
    def update(self, instance, validated_data):
        user = instance.user
        if 'first_name' in validated_data:
            user.first_name = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user.last_name = validated_data.pop('last_name')
        if 'email' in validated_data:
            user.email = validated_data.pop('email')
        user.save()
        
        return super().update(instance, validated_data)

class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Includes profile type selection.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    type = serializers.ChoiceField(choices=Profile.USER_TYPES, required=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'type', 'first_name', 'last_name']
    
    def validate(self, data):
        email = self.validated_data['email']
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Email already exists'})
        return data
    
    def create(self, validated_data):
        user_type = validated_data.pop('type')
        validated_data.pop('confirm_password')
        
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name
        )
        
        profile = user.profile
        profile.type = user_type
        profile.save()
        
        return user

class LoginSerializer(serializers.Serializer):
    """
    Serializer for login.
    Accepts username/email and password.
    """
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True, style={'input_type': 'password'})
