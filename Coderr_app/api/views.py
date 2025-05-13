# from rest_framework import viewsets, status
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from django.http import JsonResponse
# from django.contrib.auth.models import User
# from .serializers import UserSerializer

# class UserViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for managing User objects.
    
#     Provides CRUD operations for users.
#     Regular users can only see and modify their own user,
#     while staff users can access all users.
#     """
#     serializer_class = UserSerializer
    
#     def get_queryset(self):
#         """
#         Returns users filtered by permissions.
        
#         Staff users see all users, while regular users only see themselves.
        
#         Returns:
#             QuerySet: User objects based on permission,
#             or an empty QuerySet if not authenticated.
#         """
#         user = self.request.user
#         if user.is_authenticated:
#             if user.is_staff:
#                 return User.objects.all()
#             return User.objects.filter(id=user.id)
#         return User.objects.none()
    
#     def get_serializer(self, *args, **kwargs):
#         """
#         Handle both single item and list serialization.
        
#         Args:
#             *args: Variable length argument list.
#             **kwargs: Arbitrary keyword arguments.
            
#         Returns:
#             Serializer: The appropriate serializer instance.
#         """
#         if isinstance(kwargs.get('data', {}), list):
#             kwargs['many'] = True
#         return super().get_serializer(*args, **kwargs)
    
#     def list(self, request):
#         """
#         Lists users based on permissions.
        
#         Args:
#             request: The HTTP request.
            
#         Returns:
#             Response: Serialized users data.
#         """
#         users = self.get_queryset()
#         serializer = self.get_serializer(users, many=True)
#         return Response(serializer.data)
    
#     def create(self, request):
#         """
#         Creates a new user.
        
#         This is primarily for admin functionality.
#         Regular user registration should normally use a dedicated registration view.
        
#         Args:
#             request: The HTTP request containing user data.
            
#         Returns:
#             Response: Success message if created, or validation errors.
#         """
#         serializer = self.get_serializer(data=request.data)
        
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"status": "success"}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# @api_view(['GET'])
# def hello_world(request):
#     """
#     A simple API view that returns a hello message.
    
#     Args:
#         request: The HTTP request.
        
#     Returns:
#         Response: A JSON response with a "Hello World!" message.
#     """
#     return Response({"message": "Hello World!"})

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Count
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo
from .serializers import (
    OfferSerializer, OfferWithDetailsSerializer, OfferDetailSerializer, 
    ReviewSerializer, OrderSerializer, BaseInfoSerializer
)


@api_view(['GET'])
def base_info_view(request):
    """Return site statistics"""
    info = BaseInfo.get_or_create_singleton()
    serializer = BaseInfoSerializer(info)
    return Response(serializer.data)


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
        
        # Filter by creator_id if provided
        creator_id = self.request.query_params.get('creator_id')
        if creator_id:
            queryset = queryset.filter(creator_id=creator_id)
        
        # Filter by max_delivery_time if provided
        max_delivery_time = self.request.query_params.get('max_delivery_time')
        if max_delivery_time:
            try:
                max_days = int(max_delivery_time)
                # Find offers with at least one detail that has delivery time <= max_days
                queryset = queryset.filter(details__delivery_time_in_days__lte=max_days).distinct()
            except ValueError:
                pass
        
        return queryset
    
    def perform_create(self, serializer):
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
        offer_detail = serializer.save()
        
        # Create features from the features list
        features_data = self.request.data.get('features', [])
        for feature_description in features_data:
            Feature.objects.create(
                offer_detail=offer_detail,
                description=feature_description
            )
    
    def perform_update(self, serializer):
        offer_detail = serializer.save()
        
        # Update features if provided
        features_data = self.request.data.get('features')
        if features_data is not None:
            # Delete existing features
            offer_detail.features.all().delete()
            
            # Create new features
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
    
    def get_queryset(self):
        user = self.request.user
        
        # If user is a business, show orders for their offers
        # If user is a customer, show their orders
        profile_type = getattr(user, 'profile', None)
        if profile_type:
            if user.profile.type == 'business':
                return Order.objects.filter(business_user=user)
            else:
                return Order.objects.filter(customer=user)
        
        return Order.objects.none()
    
    def perform_create(self, serializer):
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
        
        # Check if status changed to completed
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
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['reviewer', 'business_user']
    ordering_fields = ['created_at', 'updated_at', 'rating']
    
    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)
        BaseInfo.update_stats()
    
    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        BaseInfo.update_stats()
