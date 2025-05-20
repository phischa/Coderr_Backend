from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo, BusinessProfile, CustomerProfile
from .serializers import (
    OfferSerializer, OfferWithDetailsSerializer, OfferDetailSerializer, 
    ReviewSerializer, OrderSerializer, BaseInfoSerializer,
    BusinessProfileSerializer, CustomerProfileSerializer, 
    BusinessProfileUpdateSerializer, CustomerProfileUpdateSerializer
)

@api_view(['GET'])
def base_info_view(request):
    """Return site statistics matching the frontend element IDs"""
    info = BaseInfo.get_or_create_singleton()
    base_data = {
        'total_users': info.total_users,
        'total_offers': info.total_offers,
        'total_completed_orders': info.total_completed_orders,
        'total_reviews': info.total_reviews
    }

    business_profile_count = BusinessProfile.objects.count()
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
        try:
            business_profile = BusinessProfile.objects.get(user=user)
            return Order.objects.filter(business_user=user)
        except BusinessProfile.DoesNotExist:
            try:
                customer_profile = CustomerProfile.objects.get(user=user)
                return Order.objects.filter(customer=user)
            except CustomerProfile.DoesNotExist:
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
        serializer.save(reviewer=self.request.user)
        BaseInfo.update_stats()
    
    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        BaseInfo.update_stats()


class BusinessProfileViewSet(viewsets.ModelViewSet):
    queryset = BusinessProfile.objects.all()
    serializer_class = BusinessProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return BusinessProfileUpdateSerializer
        return BusinessProfileSerializer
    
    @action(detail=True, methods=['GET', 'PATCH'], url_path='by-user')
    def get_by_user_id(self, request, pk=None):
        profile = get_object_or_404(BusinessProfile, user_id=pk)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = BusinessProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerProfileViewSet(viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return CustomerProfileUpdateSerializer
        return CustomerProfileSerializer
    
    @action(detail=True, methods=['GET', 'PATCH'], url_path='by-user')
    def get_by_user_id(self, request, pk=None):
        profile = get_object_or_404(CustomerProfile, user_id=pk)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = CustomerProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileCompatibilityViewSet(viewsets.ViewSet):
    """
    ViewSet für abwärtskompatible Profil-API-Endpunkte.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def retrieve(self, request, pk=None):
        """
        GET /profile/{id}/ - Gibt das passende Profil zurück (Business oder Customer)
        """
        user = get_object_or_404(User, pk=pk)
        
        try:
            profile = BusinessProfile.objects.get(user=user)
            serializer = BusinessProfileSerializer(profile)
            return Response(serializer.data)
        except BusinessProfile.DoesNotExist:
            try:
                profile = CustomerProfile.objects.get(user=user)
                serializer = CustomerProfileSerializer(profile)
                return Response(serializer.data)
            except CustomerProfile.DoesNotExist:
                return Response({"detail": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def partial_update(self, request, pk=None):
        """
        PATCH /profile/{id}/ - Aktualisiert das passende Profil
        """
        user = get_object_or_404(User, pk=pk)
        
        try:
            profile = BusinessProfile.objects.get(user=user)
            serializer = BusinessProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusinessProfile.DoesNotExist:
            try:
                profile = CustomerProfile.objects.get(user=user)
                serializer = CustomerProfileUpdateSerializer(profile, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except CustomerProfile.DoesNotExist:
                return Response({"detail": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['GET'])
    def business(self, request):
        """
        GET /profiles/business/ - Gibt alle Business-Profile zurück
        """
        profiles = BusinessProfile.objects.all()
        serializer = BusinessProfileSerializer(profiles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'])
    def customer(self, request):
        """
        GET /profiles/customer/ - Gibt alle Customer-Profile zurück
        """
        profiles = CustomerProfile.objects.all()
        serializer = CustomerProfileSerializer(profiles, many=True)
        return Response(serializer.data)
