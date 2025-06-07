import traceback
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from user_auth_app.models import Profile
from Coderr_app.models import (
    Offer, OfferDetail, Feature, Order, Review, BaseInfo
)
from .serializers import (
    OfferSerializer, OfferWithDetailsSerializer, OfferDetailSerializer, 
    ReviewSerializer, OrderSerializer, BaseInfoSerializer,
    ProfileSerializer, ProfileUpdateSerializer
)
from .permissions import IsBusinessUser, IsCustomerUser


@api_view(['GET'])
def base_info_view(request):
    """Return site statistics matching the frontend element IDs"""
    info = BaseInfo.get_or_create_singleton()
    
    business_profile_count = Profile.objects.filter(type='business').count()
    avg_rating = Review.objects.aggregate(Avg('rating'))
    average_rating = round(avg_rating['rating__avg'], 1) if avg_rating['rating__avg'] is not None else 0

    formatted_data = {
        'offer_count': info.total_offers,
        'review_count': info.total_reviews,
        'business_profile_count': business_profile_count,
        'average_rating': average_rating
    }
    
    return Response(formatted_data)


class OfferViewSet(viewsets.ModelViewSet):
    """API endpoint for offers"""
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['creator']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'min_price', 'min_delivery_time']
    
    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return OfferWithDetailsSerializer
        return OfferSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        creator_id = self.request.query_params.get('creator_id')
        if creator_id:
            queryset = queryset.filter(creator_id=creator_id)

        max_delivery_time = self.request.query_params.get('max_delivery_time')
        if max_delivery_time:
            try:
                max_days = int(max_delivery_time)
                queryset = queryset.filter(details__delivery_time_in_days__lte=max_days).distinct()
            except ValueError:
                pass
        
        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required")

        try:
            user_profile = self.request.user.profile
            if user_profile.type != 'business':
                raise PermissionDenied("Only business users can create offers")
            # No restriction on guest status - both regular and guest business users can create offers
        except Profile.DoesNotExist:
            raise PermissionDenied("User profile not found")
    
        offer = serializer.save(creator=self.request.user)
        self.create_offer_details_from_request(offer, self.request.data)
    
        BaseInfo.update_stats()

    def create_offer_details_from_request(self, offer, request_data):
        """Create offer details from the frontend form data"""
        details = request_data.get('details', [])
    
        for detail_data in details:
            try:
                detail = OfferDetail.objects.create(
                    offer=offer,
                    offer_type=detail_data.get('offer_type', 'basic'),
                    title=detail_data.get('title', f"{offer.title} - {detail_data.get('offer_type', 'basic').capitalize()}"),
                    price=float(detail_data.get('price', 0)),
                    delivery_time_in_days=int(detail_data.get('delivery_time_in_days', 1)),
                    revisions=int(detail_data.get('revisions', 1)) if detail_data.get('revisions', 1) != -1 else -1
                )
                features_list = detail_data.get('features', [])
                created_features = []
                for feature_description in features_list:
                    if feature_description.strip():
                        feature = Feature.objects.create(
                            offer_detail=detail,
                            description=feature_description.strip()
                        )
                        created_features.append(feature_description)
            
            except Exception as e:
                traceback.print_exc()

    def perform_update(self, serializer):
        """Update offer and its related details"""
        # Check if the user owns this offer
        if serializer.instance.creator != self.request.user:
            raise PermissionDenied("You can only update your own offers")
            
        offer = serializer.save()
        details_data = self.request.data.get('details', [])
        if details_data:
            for detail_data in details_data:
                detail_id = detail_data.get('id')
                offer_type = detail_data.get('offer_type')
                detail = OfferDetail.objects.get(id=detail_id, offer=offer)
                detail.title = detail_data.get('title', detail.title)
                detail.price = float(detail_data.get('price', detail.price))
                detail.delivery_time_in_days = int(detail_data.get('delivery_time_in_days', detail.delivery_time_in_days))
                detail.revisions = int(detail_data.get('revisions', detail.revisions)) if detail_data.get('revisions', detail.revisions) != -1 else -1
                detail.save()
                    
                # Update features if provided
                features_list = detail_data.get('features')
                if features_list is not None:
                    # Delete existing features
                    detail.features.all().delete()
                    # Create new features
                    for feature_description in features_list:
                        if feature_description.strip():
                            Feature.objects.create(
                                offer_detail=detail,
                                description=feature_description.strip()
                            )
    
    def perform_destroy(self, instance):
        # Check if the user owns this offer
        if instance.creator != self.request.user:
            raise PermissionDenied("You can only delete your own offers")
            
        super().perform_destroy(instance)
        BaseInfo.update_stats()


class OfferDetailViewSet(viewsets.ModelViewSet):
    """API endpoint for offer details"""
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        # Check if the offer belongs to the user
        offer_id = self.request.data.get('offer')
        offer = get_object_or_404(Offer, id=offer_id)
        
        if offer.creator != self.request.user:
            raise PermissionDenied("You can only add details to your own offers")
            
        offer_detail = serializer.save()
        features_data = self.request.data.get('features', [])
        for feature_description in features_data:
            Feature.objects.create(
                offer_detail=offer_detail,
                description=feature_description
            )
    
    def perform_update(self, serializer):
        # Check if the user owns the offer
        if serializer.instance.offer.creator != self.request.user:
            raise PermissionDenied("You can only update details of your own offers")
            
        offer_detail = serializer.save()
        features_data = self.request.data.get('features')
        if features_data is not None:
            offer_detail.features.all().delete()
            for feature_description in features_data:
                Feature.objects.create(
                    offer_detail=offer_detail,
                    description=feature_description
                )


class OrderViewSet(viewsets.ModelViewSet):
    """API endpoint for orders"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None 
    
    def get_queryset(self):
        user = self.request.user
        
        # Check if user is authenticated
        if not user.is_authenticated:
            return Order.objects.none()
            
        try:
            profile_type = user.profile.type
        except Profile.DoesNotExist:
            return Order.objects.none()
        
        if profile_type == 'business':
            return Order.objects.filter(business_user=user)
        else:  # 'customer'
            return Order.objects.filter(customer=user)
    
    def perform_create(self, serializer):
        # Check if user has a profile
        try:
            user_profile = self.request.user.profile
        except Profile.DoesNotExist:
            raise PermissionDenied("User profile not found")
            
        # Check if user is a customer (including guest customers)
        if user_profile.type != 'customer':
            raise PermissionDenied("Only customers can create orders")
        
        # No restriction on guest status - both regular and guest customers can create orders
            
        # Get offer_detail from the request data
        # The frontend might send either 'offer_detail' or 'offer_detail_id'
        offer_detail_id = (
            self.request.data.get('offer_detail') or 
            self.request.data.get('offer_detail_id')
        )
        
        if not offer_detail_id:
            raise ValidationError({
                'offer_detail': 'This field is required'
            })
            
        try:
            offer_detail = OfferDetail.objects.get(id=offer_detail_id)
        except OfferDetail.DoesNotExist:
            raise ValidationError({
                'offer_detail': 'Invalid offer detail ID'
            })
            
        business_user = offer_detail.offer.creator
        
        # Save the order with the required relationships
        serializer.save(
            customer=self.request.user,
            business_user=business_user,
            offer_detail=offer_detail
        )
    
    def perform_update(self, serializer):
        # Check if user owns this order (as business or customer)
        order = serializer.instance
        user = self.request.user
        
        # Business users (including guests) can update order status
        if user == order.business_user:
            # Business users can update orders they're assigned to
            pass
        elif user == order.customer:
            # Customers can also update their own orders (e.g., cancel)
            pass
        else:
            raise PermissionDenied("You can only update orders you're involved in")
        
        old_status = serializer.instance.status
        instance = serializer.save()
        if old_status != 'completed' and instance.status == 'completed':
            BaseInfo.update_stats()
    
    @action(detail=False, methods=['GET'], url_path='order-count/(?P<user_id>[^/.]+)')
    def order_count(self, request, user_id=None):
        """Count in-progress orders for a business user"""
        count = Order.objects.filter(
            business_user_id=user_id,
            status='in_progress'
        ).count()
        return Response({'order_count': count})
    
    @action(detail=False, methods=['GET'], url_path='completed-order-count/(?P<user_id>[^/.]+)')
    def completed_order_count(self, request, user_id=None):
        """Count completed orders for a business user"""
        count = Order.objects.filter(
            business_user_id=user_id,
            status='completed'
        ).count()
        return Response({'completed_order_count': count})


class ReviewViewSet(viewsets.ModelViewSet):
    """API endpoint for reviews"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['reviewer', 'business_user']  # Behalten wir für Rückwärtskompatibilität
    ordering_fields = ['created_at', 'updated_at', 'rating']
    
    def get_queryset(self):
        """
        Custom queryset filtering to support both:
        - Standard DjangoFilter: ?business_user=X&reviewer=Y
        - Frontend convention: ?business_user_id=X&reviewer_id=Y
        """
        queryset = Review.objects.all()
        
        # Frontend-Style Parameter (mit _id Suffix)
        business_user_id = self.request.query_params.get('business_user_id')
        reviewer_id = self.request.query_params.get('reviewer_id')
        
        # Standard DjangoFilter Parameter (ohne _id Suffix) - für Rückwärtskompatibilität
        business_user = self.request.query_params.get('business_user')
        reviewer = self.request.query_params.get('reviewer')
        
        # Filter für business_user (Frontend hat Priorität)
        if business_user_id is not None:
            queryset = queryset.filter(business_user_id=business_user_id)
        elif business_user is not None:
            queryset = queryset.filter(business_user_id=business_user)
        
        # Filter für reviewer (Frontend hat Priorität)
        if reviewer_id is not None:
            queryset = queryset.filter(reviewer_id=reviewer_id)
        elif reviewer is not None:
            queryset = queryset.filter(reviewer_id=reviewer)
        
        # Sortierung anwenden
        ordering = self.request.query_params.get('ordering')
        if ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-updated_at')  # Standard-Sortierung
            
        return queryset
    
    @action(detail=False, methods=['GET'], url_path='business/(?P<business_user_id>[^/.]+)')
    def business_reviews(self, request, business_user_id=None):
        """
        Get all reviews for a specific business user.
        URL: /api/reviews/business/{business_user_id}/
        """
        try:
            business_user = User.objects.get(id=business_user_id)
            # Verify it's actually a business user
            if business_user.profile.type != 'business':
                return Response(
                    {'error': 'User is not a business user'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Business user not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get reviews for this business user
        reviews = Review.objects.filter(business_user_id=business_user_id)
        
        # Apply ordering
        ordering = request.query_params.get('ordering', '-updated_at')
        if ordering:
            reviews = reviews.order_by(ordering)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'], url_path='reviewer/(?P<reviewer_id>[^/.]+)')
    def reviewer_reviews(self, request, reviewer_id=None):
        """
        Get all reviews by a specific reviewer (customer).
        URL: /api/reviews/reviewer/{reviewer_id}/
        """
        try:
            reviewer = User.objects.get(id=reviewer_id)
            # Verify it's actually a customer user
            if reviewer.profile.type != 'customer':
                return Response(
                    {'error': 'User is not a customer user'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Reviewer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get reviews by this reviewer
        reviews = Review.objects.filter(reviewer_id=reviewer_id)
        
        # Apply ordering
        ordering = request.query_params.get('ordering', '-updated_at')
        if ordering:
            reviews = reviews.order_by(ordering)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        # Check if user is a customer (including guest customers)
        try:
            user_profile = self.request.user.profile
            if user_profile.type != 'customer':
                raise PermissionDenied("Only customers can submit reviews")
            # No restriction on guest status - both regular and guest customers can create reviews
        except Profile.DoesNotExist:
            raise PermissionDenied("User profile not found")
            
        serializer.save(reviewer=self.request.user)
        BaseInfo.update_stats()
    
    def perform_destroy(self, instance):
        # Check if the user owns this review
        if instance.reviewer != self.request.user:
            raise PermissionDenied("You can only delete your own reviews")
            
        super().perform_destroy(instance)
        BaseInfo.update_stats()


class ProfileViewSet(viewsets.ModelViewSet):
    """API endpoint for user profiles"""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['type']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'location']
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ProfileUpdateSerializer
        return ProfileSerializer
        
    def get_queryset(self):
        queryset = super().get_queryset()
        user_type = self.request.query_params.get('type')
        if user_type:
            queryset = queryset.filter(type=user_type)
        return queryset

    @action(detail=True, methods=['GET', 'PATCH'], url_path='by-user')
    def get_by_user_id(self, request, pk=None):
        """Get profile by user ID instead of profile ID"""
        profile = get_object_or_404(Profile, user_id=pk)
    
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
    
        elif request.method == 'PATCH':
            # Only allow users to update their own profile
            if request.user.id != int(pk) and not request.user.is_staff:
                return Response(
                    {'error': 'You can only update your own profile'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['GET'])
    def business(self, request):
        """List all business profiles"""
        profiles = Profile.objects.filter(type='business')
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'])
    def customer(self, request):
        """List all customer profiles"""
        profiles = Profile.objects.filter(type='customer')
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)
