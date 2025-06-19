from rest_framework import serializers
from django.contrib.auth.models import User
from user_auth_app.models import Profile

RESERVED_USERNAMES = ["andrey", "kevin"]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """

    class Meta:
        model = Profile
        fields = ["id", "username", "first_name", "last_name", "email"]
        read_only_fields = ["id"]


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profile model.
    Ensures that required fields return empty strings instead of null values.
    """

    username = serializers.ReadOnlyField()
    # Override fields to ensure empty string instead of null
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    tel = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
            "email",
            "created_at",
        ]
        read_only_fields = ["user", "created_at"]

    def get_first_name(self, obj):
        """Return empty string if first_name is None or empty"""
        return obj.first_name or ""

    def get_last_name(self, obj):
        """Return empty string if last_name is None or empty"""
        return obj.last_name or ""

    def get_email(self, obj):
        """Return the user's email address"""
        return obj.user.email or ""

    def get_location(self, obj):
        """Return empty string if location is None or empty"""
        return obj.location or ""

    def get_tel(self, obj):
        """Return empty string if tel is None or empty"""
        return obj.tel or ""

    def get_description(self, obj):
        """Return empty string if description is None or empty"""
        return obj.description or ""

    def get_working_hours(self, obj):
        """Return empty string if working_hours is None or empty"""
        return obj.working_hours or ""


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Profile objects.
    Allows updating both User and Profile fields.
    """

    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = [
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "first_name",
            "last_name",
            "email",
        ]

    def update(self, instance, validated_data):
        """
        Update profile and related user fields.
        Ensures empty strings are saved instead of None.
        """
        user = instance.user
        
        # Update user fields
        if "first_name" in validated_data:
            user.first_name = validated_data.pop("first_name") or ""
        if "last_name" in validated_data:
            user.last_name = validated_data.pop("last_name") or ""
        if "email" in validated_data:
            user.email = validated_data.pop("email")
        user.save()

        # Update profile fields, ensuring empty strings for blank values
        for field in ["location", "tel", "description", "working_hours"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field] or "")

        instance.save()
        return instance


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for customer profile listings.
    Ensures empty strings instead of null values.
    """

    username = serializers.ReadOnlyField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    uploaded_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "user",
            "username", 
            "first_name",
            "last_name",
            "file",
            "uploaded_at",
            "type",
        ]

    def get_first_name(self, obj):
        return obj.first_name or ""

    def get_last_name(self, obj):
        return obj.last_name or ""


class BusinessProfileSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for business profile listings.
    Ensures empty strings instead of null values.
    """

    username = serializers.ReadOnlyField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    tel = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "user",
            "username",
            "first_name", 
            "last_name",
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
        ]

    def get_first_name(self, obj):
        return obj.first_name or ""

    def get_last_name(self, obj):
        return obj.last_name or ""

    def get_location(self, obj):
        return obj.location or ""

    def get_tel(self, obj):
        return obj.tel or ""

    def get_description(self, obj):
        return obj.description or ""

    def get_working_hours(self, obj):
        return obj.working_hours or ""


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Includes profile type selection.
    """

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    repeated_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    type = serializers.ChoiceField(choices=Profile.USER_TYPES, required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email", 
            "password",
            "repeated_password",
            "type",
            "first_name",
            "last_name",
        ]

    def validate_username(self, value):
        """
        Check that the username is not reserved for guest users.
        """
        if value.lower() in [name.lower() for name in RESERVED_USERNAMES]:
            raise serializers.ValidationError(
                f"The username '{value}' is reserved and cannot be used for registration."
            )
        return value

    def validate(self, data):
        if data["password"] != data["repeated_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        return data

    def create(self, validated_data):
        user_type = validated_data.pop("type")
        validated_data.pop("repeated_password")

        first_name = validated_data.pop("first_name", "")
        last_name = validated_data.pop("last_name", "")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=first_name,
            last_name=last_name,
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
    password = serializers.CharField(
        max_length=128, write_only=True, style={"input_type": "password"}
    )
