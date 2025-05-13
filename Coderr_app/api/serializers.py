

# class UserSerializer(serializers.ModelSerializer):
#     """
#     Serializer for Django's User model.
    
#     Ensures that the password is only used for writing and is securely stored.
#     """
    
#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'password']
#         extra_kwargs = {'password': {'write_only': True}}
    
#     def create(self, validated_data):
#         """
#         Creates a new user.
        
#         Uses Django's create_user method to ensure secure password hashing.
        
#         Args:
#             validated_data: Dict with validated data for creating the user
            
#         Returns:
#             User: Newly created User object with securely stored password
#         """
#         user = User.objects.create_user(
#             username=validated_data['username'],
#             email=validated_data.get('email', ''),
#             password=validated_data.get('password', '')
#         )
#         return user

from rest_framework import serializers
from django.contrib.auth.models import User
from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ['id', 'description']


class OfferDetailSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer', 'offer_type', 'title', 'revisions', 
                  'delivery_time_in_days', 'price', 'features']
    
    def get_features(self, obj):
        # Return just the feature descriptions as a list of strings
        return [feature.description for feature in obj.features.all()]


class OfferDetailWithFeaturesSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer_type', 'title', 'revisions', 
                    'delivery_time_in_days', 'price', 'features']
    
    def get_features(self, obj):
        # Return just the feature descriptions as a list of strings
        return [feature.description for feature in obj.features.all()]


class OfferSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()
    min_price = serializers.ReadOnlyField()
    min_delivery_time = serializers.ReadOnlyField()
    user = serializers.ReadOnlyField()
    
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
    details = OfferDetailWithFeaturesSerializer(many=True, read_only=True)
    min_price = serializers.ReadOnlyField()
    min_delivery_time = serializers.ReadOnlyField()
    user = serializers.ReadOnlyField()
    
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'image', 'created_at', 'updated_at',
                    'min_price', 'min_delivery_time', 'details', 'user']


class ReviewSerializer(serializers.ModelSerializer):
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
    customer_username = serializers.SerializerMethodField()
    business_username = serializers.SerializerMethodField()
    title = serializers.ReadOnlyField()
    delivery_time_in_days = serializers.ReadOnlyField()
    revisions = serializers.ReadOnlyField()
    price = serializers.ReadOnlyField()
    features = serializers.ReadOnlyField()
    customer_user = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = ['id', 'customer', 'business_user', 'customer_username', 'business_username',
                    'offer_detail', 'status', 'created_at', 'updated_at', 
                    'title', 'delivery_time_in_days', 'revisions', 'price', 'features',
                    'customer_user']
    
    def get_customer_username(self, obj):
        return obj.customer.username
    
    def get_business_username(self, obj):
        return obj.business_user.username


class BaseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseInfo
        fields = ['total_users', 'total_offers', 'total_completed_orders', 'total_reviews']
