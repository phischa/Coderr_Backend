from rest_framework import serializers
from django.contrib.auth.models import User
from user_auth_app.models import Profile
from Coderr_app.models import (
    Offer, OfferDetail, Feature, Order, Review, BaseInfo
)

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profile model.
    Includes user data through properties.
    """
    username = serializers.ReadOnlyField()
    first_name = serializers.ReadOnlyField()
    last_name = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    
    class Meta:
        model = Profile
        fields = ['id', 'user', 'file', 'location', 'tel', 'description', 'working_hours', 
                    'type', 'created_at', 'username', 'first_name', 'last_name', 'email', 'is_guest']
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
        # Update User model fields
        user = instance.user
        if 'first_name' in validated_data:
            user.first_name = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user.last_name = validated_data.pop('last_name')
        if 'email' in validated_data:
            user.email = validated_data.pop('email')
        user.save()
        
        # Update Profile model fields
        return super().update(instance, validated_data)


class FeatureSerializer(serializers.ModelSerializer):
    """
    Serializer for the Feature model.
    """
    class Meta:
        model = Feature
        fields = ['id', 'description']


class OfferDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for OfferDetail.
    Handles default values for null fields to match frontend expectations.
    """
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer', 'offer_type', 'title', 'revisions', 
                    'delivery_time_in_days', 'price', 'features']
    
    def get_features(self, obj):
        # Return just the feature descriptions as a list of strings
        return [feature.description for feature in obj.features.all()]
    
    def to_representation(self, instance):
        """
        Override to provide default values for null fields.
        This ensures the frontend receives consistent data regardless of 
        whether it expects null or default values.
        """
        data = super().to_representation(instance)
        
        # Replace null values with sensible defaults
        if data.get('revisions') is None:
            data['revisions'] = 1
        if data.get('delivery_time_in_days') is None:
            data['delivery_time_in_days'] = 1
        if data.get('price') is None:
            data['price'] = 0
            
        return data


class OfferDetailWithFeaturesSerializer(serializers.ModelSerializer):
    """
    Serializer for OfferDetail with expanded features.
    Handles default values for null fields.
    """
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer_type', 'title', 'revisions', 
                    'delivery_time_in_days', 'price', 'features']
    
    def get_features(self, obj):
        # Return just the feature descriptions as a list of strings
        return [feature.description for feature in obj.features.all()]
    
    def to_representation(self, instance):
        """
        Override to provide default values for null fields.
        """
        data = super().to_representation(instance)
        
        # Replace null values with sensible defaults
        if data.get('revisions') is None:
            data['revisions'] = 1
        if data.get('delivery_time_in_days') is None:
            data['delivery_time_in_days'] = 1
        if data.get('price') is None:
            data['price'] = 0
            
        return data


class OfferSerializer(serializers.ModelSerializer):
    """
    Serializer for Offer model.
    """
    user = serializers.ReadOnlyField(source='creator.id')
    details = serializers.SerializerMethodField()
    min_price = serializers.ReadOnlyField()
    min_delivery_time = serializers.ReadOnlyField()
    user_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'image', 'created_at', 'updated_at',
                    'min_price', 'min_delivery_time', 'details', 'user', 'user_details'] 
    
    def get_details(self, obj):
        return [
            {
                'id': detail.id,
                'url': f'/offerdetails/{detail.id}/'
            }
            for detail in obj.details.all()
        ]
    
    def get_user_details(self, obj):
        """Return user details as per documentation"""
        return {
            'first_name': obj.creator.first_name,
            'last_name': obj.creator.last_name,
            'username': obj.creator.username
        }


class OfferWithDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for Offer with expanded details.
    """
    details = OfferDetailWithFeaturesSerializer(many=True, read_only=True)
    min_price = serializers.ReadOnlyField()
    min_delivery_time = serializers.ReadOnlyField()
    user = serializers.ReadOnlyField(source='creator.id')
    
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'image', 'created_at', 'updated_at',
                    'min_price', 'min_delivery_time', 'details', 'user']



class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Review model.
    """
    reviewer_username = serializers.SerializerMethodField()
    business_user_username = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = ['id', 'reviewer', 'business_user', 'rating', 'description', 
                    'created_at', 'updated_at', 'reviewer_username', 'business_user_username']
        read_only_fields = ['reviewer', 'created_at', 'updated_at']
    
    def get_reviewer_username(self, obj):
        return obj.reviewer.username
    
    def get_business_user_username(self, obj):
        return obj.business_user.username
    
    def validate_business_user(self, value):
        """Validate that the business_user exists and is actually a business user"""
        try:
            user = User.objects.get(id=value.id)
            profile = user.profile
            if profile.type != 'business':
                raise serializers.ValidationError("The specified user is not a business user")
        except User.DoesNotExist:
            raise serializers.ValidationError("Business user does not exist")
        except Profile.DoesNotExist:
            raise serializers.ValidationError("User profile does not exist")
        return value
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model.
    Accepts offer_detail_id to match frontend expectations.
    Includes all necessary fields from the related OfferDetail.
    """

    offer_detail_id = serializers.IntegerField(write_only=True, required=False)
    customer_username = serializers.SerializerMethodField()
    business_username = serializers.SerializerMethodField()
    
    # Add the missing fields from the model properties
    features = serializers.ReadOnlyField()
    title = serializers.ReadOnlyField()
    price = serializers.ReadOnlyField()
    delivery_time_in_days = serializers.ReadOnlyField()
    revisions = serializers.ReadOnlyField()
    offer_type = serializers.ReadOnlyField()  # ADD THIS LINE - Missing from original
    customer_user = serializers.ReadOnlyField()  # This returns customer.id
    
    class Meta:
        model = Order
        fields = [
            'id', 
            'offer_detail_id',      
            'offer_detail',         
            'customer', 
            'customer_user',       
            'business_user', 
            'customer_username',
            'business_username',
            'status', 
            'created_at', 
            'updated_at',
            'features',
            'title',
            'price',
            'delivery_time_in_days',
            'revisions',
            'offer_type' 
        ]
        read_only_fields = ['id', 'customer', 'business_user', 'offer_detail', 'created_at', 'updated_at']
    
    def get_customer_username(self, obj):
        """Return the customer's username."""
        return obj.customer.username if obj.customer else None
    
    def get_business_username(self, obj):
        """Return the business user's username."""
        return obj.business_user.username if obj.business_user else None
    
    def validate_offer_detail_id(self, value):
        """Validate that the offer detail exists."""
        if not OfferDetail.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid offer detail ID")
        return value



class BaseInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for BaseInfo model.
    """
    class Meta:
        model = BaseInfo
        fields = ['total_users', 'total_offers', 'total_completed_orders', 'total_reviews']