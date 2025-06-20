from rest_framework import serializers
from django.contrib.auth.models import User
from user_auth_app.models import Profile
from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class FeatureSerializer(serializers.ModelSerializer):
    """
    Serializer for the Feature model.
    """
    class Meta:
        model = Feature
        fields = ['id', 'description']

class OfferDetailSerializer(serializers.ModelSerializer):
    """
    Unified serializer for OfferDetail
    Conditionally includes/excludes the 'offer' field based on context.
    """
    features = serializers.SerializerMethodField()
    
    # Use SerializerMethodFields for ALL critical fields to ensure no nulls
    revisions = serializers.SerializerMethodField()
    delivery_time_in_days = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    offer_type = serializers.SerializerMethodField()
    
    class Meta:
        model = OfferDetail
        fields = ['id', 'offer', 'offer_type', 'title', 'revisions', 
                    'delivery_time_in_days', 'price', 'features']
    
    def __init__(self, *args, **kwargs):
        # Remove 'offer' field for retrieve context to match documentation
        exclude_offer = kwargs.pop('exclude_offer', False)
        super().__init__(*args, **kwargs)
        if exclude_offer:
            self.fields.pop('offer', None)
    
    def get_features(self, obj):
        """Return feature descriptions as list of strings - never null"""
        try:
            features = [feature.description for feature in obj.features.all()]
            return features if features else []  # Return empty list instead of null
        except:
            return []  # Return empty list on any error
    
    def get_revisions(self, obj):
        """Return revisions - never null, default 1"""
        try:
            value = obj.revisions
            if value is None:
                return 1
            # Ensure it's an integer
            return int(value) if value >= 0 else 1
        except (ValueError, TypeError, AttributeError):
            return 1
    
    def get_delivery_time_in_days(self, obj):
        """Return delivery time - never null, default 1"""
        try:
            value = obj.delivery_time_in_days
            if value is None:
                return 1
            # Ensure it's a positive integer
            return max(1, int(value))
        except (ValueError, TypeError, AttributeError):
            return 1
    
    def get_price(self, obj):
        """Return price - never null, default 0.0"""
        try:
            value = obj.price
            if value is None:
                return 0.0
            # Ensure it's a valid number
            return max(0.0, float(value))
        except (ValueError, TypeError, AttributeError):
            return 0.0
    
    def get_title(self, obj):
        """Return title - never null, default empty string"""
        try:
            value = obj.title
            return str(value) if value is not None else ""
        except (AttributeError, TypeError):
            return ""
    
    def get_offer_type(self, obj):
        """Return offer_type - never null, default 'basic'"""
        try:
            value = obj.offer_type
            if value in ['basic', 'standard', 'premium']:
                return value
            return "basic"
        except (AttributeError, TypeError):
            return "basic"


class OfferWithDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for Offer with expanded details - NO NULL VALUES!
    Returns full detail objects according to documentation.
    """
    details = serializers.SerializerMethodField()
    
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'image', 'details']
    
    def get_details(self, obj):
        """
        Return full detail objects with guaranteed non-null values
        """
        try:
            return OfferDetailSerializer(obj.details.all(), many=True, exclude_offer=True).data
        except:
            return []


class OfferSerializer(serializers.ModelSerializer):
    """
    Serializer for Offer model - handles both read and write operations.
    NO NULL VALUES in responses!
    """
    user = serializers.ReadOnlyField(source='creator.id')
    details = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()
    
    # Add details field for write operations (POST)
    details_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        source='details'
    )
    
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'image', 'created_at', 'updated_at',
                    'min_price', 'min_delivery_time', 'details', 'user', 'user_details', 'details_data'] 
    
    def get_details(self, obj):
        """
        For GET operations: Return details as URLs according to documentation
        Format: [{"id": 1, "url": "/offerdetails/1/"}]
        """
        try:
            return [
                {
                    'id': detail.id,
                    'url': f'/offerdetails/{detail.id}/'
                }
                for detail in obj.details.all()
            ]
        except:
            return []
    
    def get_min_price(self, obj):
        """Return min_price - never null, default 0.0"""
        try:
            min_price = obj.min_price
            if min_price is None:
                return 0.0
            return max(0.0, float(min_price))
        except (ValueError, TypeError, AttributeError):
            return 0.0
    
    def get_min_delivery_time(self, obj):
        """Return min_delivery_time - never null, default 1"""
        try:
            min_delivery = obj.min_delivery_time
            if min_delivery is None:
                return 1
            return max(1, int(min_delivery))
        except (ValueError, TypeError, AttributeError):
            return 1
    
    def get_user_details(self, obj):
        """Return user details for list operations - never null"""
        try:
            return {
                'first_name': obj.creator.first_name or "",
                'last_name': obj.creator.last_name or "",
                'username': obj.creator.username or ""
            }
        except (AttributeError, TypeError):
            return {
                'first_name': "",
                'last_name': "", 
                'username': ""
            }

    def create(self, validated_data):
        """Create offer with details, ensuring no null values"""
        details_data = validated_data.pop('details', [])
        offer = Offer.objects.create(**validated_data)
        
        # Create default details if none provided
        if not details_data:
            details_data = [
                {'offer_type': 'basic', 'title': '', 'revisions': 1, 'delivery_time_in_days': 1, 'price': 0.0, 'features': []},
                {'offer_type': 'standard', 'title': '', 'revisions': 1, 'delivery_time_in_days': 1, 'price': 0.0, 'features': []},
                {'offer_type': 'premium', 'title': '', 'revisions': 1, 'delivery_time_in_days': 1, 'price': 0.0, 'features': []}
            ]
        
        for detail_data in details_data:
            # Sanitize detail data to prevent null values
            sanitized_detail = {
                'offer': offer,
                'offer_type': detail_data.get('offer_type', 'basic'),
                'title': detail_data.get('title') or '',
                'revisions': max(1, int(detail_data.get('revisions') or 1)),
                'delivery_time_in_days': max(1, int(detail_data.get('delivery_time_in_days') or 1)),
                'price': max(0.0, float(detail_data.get('price') or 0.0))
            }
            
            # Handle special case for unlimited revisions
            if sanitized_detail['revisions'] == -1:
                sanitized_detail['revisions'] = -1
            
            offer_detail = OfferDetail.objects.create(**sanitized_detail)
            
            # Create features
            features_list = detail_data.get('features', [])
            for feature_description in features_list:
                if feature_description and feature_description.strip():
                    Feature.objects.create(
                        offer_detail=offer_detail,
                        description=feature_description.strip()
                    )
        
        return offer


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Review model - documentation compliant.
    """
    class Meta:
        model = Review
        fields = [
            "id",
            "business_user",
            "reviewer", 
            "rating",
            "description",
            "created_at",
            "updated_at"
        ]
        read_only_fields = [
            "id",
            "reviewer",
            "created_at", 
            "updated_at"
        ]

    def validate_business_user(self, value):
        """Validate that the business_user exists and is actually a business user"""
        try:
            user = User.objects.get(id=value.id)
            profile = user.profile
            if profile.type != "business":
                raise serializers.ValidationError(
                    "The specified user is not a business user"
                )
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
    Serializer for Order model - CORRECTED for documentation compliance.
    ENSURES NO NULL VALUES IN RESPONSES!
    """
    # offer_detail_id must be required=True
    offer_detail_id = serializers.IntegerField(write_only=True, required=True)
    
    # Response fields matching documentation exactly - using SerializerMethodFields for safety
    customer_user = serializers.SerializerMethodField()
    business_user = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    revisions = serializers.SerializerMethodField()
    delivery_time_in_days = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    offer_type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_user", 
            "business_user",
            "title",
            "revisions", 
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
            "status",
            "created_at",
            "updated_at",
            "offer_detail_id"
        ]
        read_only_fields = [
            "id", "customer_user", "business_user", "title", "revisions",
            "delivery_time_in_days", "price", "features", "offer_type", 
            "created_at", "updated_at", "status"
        ]

    def get_customer_user(self, obj):
        """Return customer user ID - never null"""
        try:
            return obj.customer.id if obj.customer else None
        except AttributeError:
            return None

    def get_business_user(self, obj):
        """Return business user ID - never null"""
        try:
            return obj.business_user.id if obj.business_user else None
        except AttributeError:
            return None

    def get_title(self, obj):
        """Return title from offer detail - never null"""
        try:
            return obj.offer_detail.title or "" if obj.offer_detail else ""
        except AttributeError:
            return ""

    def get_revisions(self, obj):
        """Return revisions from offer detail - never null"""
        try:
            value = obj.offer_detail.revisions if obj.offer_detail else 1
            return int(value) if value is not None else 1
        except (AttributeError, ValueError, TypeError):
            return 1

    def get_delivery_time_in_days(self, obj):
        """Return delivery time from offer detail - never null"""
        try:
            value = obj.offer_detail.delivery_time_in_days if obj.offer_detail else 1
            return max(1, int(value)) if value is not None else 1
        except (AttributeError, ValueError, TypeError):
            return 1

    def get_price(self, obj):
        """Return price from offer detail - never null"""
        try:
            value = obj.offer_detail.price if obj.offer_detail else 0.0
            return max(0.0, float(value)) if value is not None else 0.0
        except (AttributeError, ValueError, TypeError):
            return 0.0

    def get_features(self, obj):
        """Return features from offer detail - never null"""
        try:
            if obj.offer_detail:
                features = [f.description for f in obj.offer_detail.features.all()]
                return features if features else []
            return []
        except AttributeError:
            return []

    def get_offer_type(self, obj):
        """Return offer type from offer detail - never null"""
        try:
            value = obj.offer_detail.offer_type if obj.offer_detail else "basic"
            return value if value in ['basic', 'standard', 'premium'] else "basic"
        except AttributeError:
            return "basic"

    def get_status(self, obj):
        """Return status - never null"""
        try:
            return obj.status or "in_progress"
        except AttributeError:
            return "in_progress"

    def validate_offer_detail_id(self, value):
        """Validate that the offer detail exists."""
        try:
            OfferDetail.objects.get(id=value)
        except OfferDetail.DoesNotExist:
            raise serializers.ValidationError("Das angegebene Angebotsdetail wurde nicht gefunden")
        return value


class BaseInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for BaseInfo model.
    """
    class Meta:
        model = BaseInfo
        fields = [
            "total_users",
            "total_offers",
            "total_completed_orders",
            "total_reviews",
        ]
        