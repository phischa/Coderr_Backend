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
    """
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer', 'offer_type', 'title', 'revisions', 
                    'delivery_time_in_days', 'price', 'features']
    
    def get_features(self, obj):
        # Return just the feature descriptions as a list of strings
        return [feature.description for feature in obj.features.all()]


class OfferDetailWithFeaturesSerializer(serializers.ModelSerializer):
    """
    Serializer for OfferDetail with expanded features.
    """
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer_type', 'title', 'revisions', 
                    'delivery_time_in_days', 'price', 'features']
    
    def get_features(self, obj):
        # Return just the feature descriptions as a list of strings
        return [feature.description for feature in obj.features.all()]


class OfferSerializer(serializers.ModelSerializer):
    """
    Serializer for Offer model.
    """
    user = serializers.ReadOnlyField(source='creator.id')
    details = serializers.SerializerMethodField()
    min_price = serializers.ReadOnlyField()
    min_delivery_time = serializers.ReadOnlyField()
    
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'image', 'created_at', 'updated_at',
                    'min_price', 'min_delivery_time', 'details', 'user']
    
    def get_details(self, obj):
        return [
            {
                'id': detail.id,
                'offer_type': detail.offer_type
            }
            for detail in obj.details.all()
        ]


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
    
    def get_reviewer_username(self, obj):
        return obj.reviewer.username
    
    def get_business_user_username(self, obj):
        return obj.business_user.username


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model.
    """
    customer_username = serializers.SerializerMethodField()
    business_username = serializers.SerializerMethodField()
    title = serializers.ReadOnlyField()
    delivery_time_in_days = serializers.ReadOnlyField()
    revisions = serializers.ReadOnlyField()
    price = serializers.ReadOnlyField()
    features = serializers.ReadOnlyField()
    customer_user = serializers.ReadOnlyField()
    offer_detail_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Order
        fields = ['id', 'customer', 'business_user', 'customer_username', 'business_username',
                    'offer_detail', 'offer_detail_id', 'status', 'created_at', 'updated_at', 
                    'title', 'delivery_time_in_days', 'revisions', 'price', 'features',
                    'customer_user']
        read_only_fields = ['customer', 'business_user']
    
    def get_customer_username(self, obj):
        return obj.customer.username
    
    def get_business_username(self, obj):
        return obj.business_user.username
    
    def validate(self, data):
        """
        Ensure either offer_detail or offer_detail_id is provided
        """
        if not data.get('offer_detail') and not data.get('offer_detail_id'):
            raise serializers.ValidationError(
                "Either 'offer_detail' or 'offer_detail_id' must be provided"
            )
        return data


class BaseInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for BaseInfo model.
    """
    class Meta:
        model = BaseInfo
        fields = ['total_users', 'total_offers', 'total_completed_orders', 'total_reviews']