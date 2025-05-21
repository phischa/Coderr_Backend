from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny, BasePermission
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

class IsBusinessUser(BasePermission):
    """
    Custom permission to only allow business users to access a view.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                hasattr(request.user, 'profile') and 
                request.user.profile.type == 'business')

class IsCustomerUser(BasePermission):
    """
    Custom permission to only allow customer users to access a view.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                hasattr(request.user, 'profile') and 
                request.user.profile.type == 'customer')

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
        # Check if user is a business user
        if self.request.user.profile.type != 'business':
            raise PermissionDenied("Only business users can create offers")
        
        serializer.save(creator=self.request.user)
        BaseInfo.update_stats()
    
    def perform_destroy(self, instance):
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
        profile_type = user.profile.type
        
        if profile_type == 'business':
            return Order.objects.filter(business_user=user)
        else:  # 'customer'
            return Order.objects.filter(customer=user)
    
    def perform_create(self, serializer):
        # Check if user is a customer
        if self.request.user.profile.type != 'customer':
            raise PermissionDenied("Only customers can create orders")
            
        offer_detail_id = self.request.data.get('offer_detail_id')
        if not offer_detail_id:
            return Response(
                {'error': 'offer_detail_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        offer_detail = get_object_or_404(OfferDetail, id=offer_detail_id)
        business_user = offer_detail.offer.creator
        serializer.save(
            customer=self.request.user,
            business_user=business_user,
            offer_detail=offer_detail
        )
    
    def perform_update(self, serializer):
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
    filterset_fields = ['reviewer', 'business_user']
    ordering_fields = ['created_at', 'updated_at', 'rating']
    
    def perform_create(self, serializer):
        # Check if user is a customer
        if self.request.user.profile.type != 'customer':
            raise PermissionDenied("Only customers can submit reviews")
            
        serializer.save(reviewer=self.request.user)
        BaseInfo.update_stats()
    
    def perform_destroy(self, instance):
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
