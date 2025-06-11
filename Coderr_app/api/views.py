import traceback
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from django.http import Http404
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
from .permissions import IsBusinessUser, IsCustomerUser, IsOwnerOrReadOnly


@api_view(['GET'])
def base_info_view(request):
    """
    GET /api/base-info/
    
    Ruft allgemeine Basisinformationen zur Plattform ab, einschließlich der Anzahl 
    der Bewertungen, des durchschnittlichen Bewertungsergebnisses, der Anzahl der 
    Geschäftsnutzer und der Anzahl der Angebote.
    
    Status Codes:
    - 200: Die Basisinformationen wurden erfolgreich abgerufen
    - 500: Interner Serverfehler
    
    No Permissions required
    """
    try:
        # Update stats to ensure we have current data
        info = BaseInfo.update_stats()
        
        # Calculate business profile count in real-time for accuracy
        business_profile_count = Profile.objects.filter(type='business').count()
        
        # Calculate average rating based on all reviews, rounded to 1 decimal place
        avg_rating = Review.objects.aggregate(Avg('rating'))
        average_rating = round(avg_rating['rating__avg'], 1) if avg_rating['rating__avg'] is not None else 0.0

        # Format response exactly as per documentation
        formatted_data = {
            'review_count': info.total_reviews,
            'average_rating': average_rating,
            'business_profile_count': business_profile_count,
            'offer_count': info.total_offers
        }
        
        return Response(formatted_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Handle any internal server errors
        return Response(
            {'error': 'Interner Serverfehler'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class OfferViewSet(viewsets.ModelViewSet):
    """API endpoint for offers with proper status codes and permissions"""
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['creator']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'min_price', 'min_delivery_time']
    
    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return OfferWithDetailsSerializer
        return OfferSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /api/offers/ - Return 200 OK, 400 Bad Request, 500 Internal Server Error"""
        try:
            # Validate query parameters
            self.validate_query_parameters(request)
            
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e.detail) if hasattr(e, 'detail') else str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def validate_query_parameters(self, request):
        """Validate query parameters as per documentation"""
        creator_id = request.query_params.get('creator_id')
        if creator_id:
            try:
                int(creator_id)
            except ValueError:
                raise ValidationError({'creator_id': 'Must be a valid integer'})
        
        min_price = request.query_params.get('min_price')
        if min_price:
            try:
                float(min_price)
            except ValueError:
                raise ValidationError({'min_price': 'Must be a valid number'})
        
        max_delivery_time = request.query_params.get('max_delivery_time')
        if max_delivery_time:
            try:
                max_days = int(max_delivery_time)
                if max_days < 0:
                    raise ValidationError({'max_delivery_time': 'Must be a positive integer'})
            except ValueError:
                raise ValidationError({'max_delivery_time': 'Must be a valid integer'})
        
        page_size = request.query_params.get('page_size')
        if page_size:
            try:
                size = int(page_size)
                if size < 1 or size > 100:  # reasonable limits
                    raise ValidationError({'page_size': 'Must be between 1 and 100'})
            except ValueError:
                raise ValidationError({'page_size': 'Must be a valid integer'})
    
    def retrieve(self, request, *args, **kwargs):
        """GET /api/offers/{id}/ - Return 200 OK, 401 Unauthorized, 404 Not Found, 500 Internal Server Error"""
        try:
            # Authentication is handled by permission class
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(
                {'error': 'Das Angebot mit der angegebenen ID wurde nicht gefunden'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """POST /api/offers/ - Return 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 500 Internal Server Error"""
        try:
            # Check authentication first
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check business user permission using existing IsBusinessUser logic
            try:
                user_profile = request.user.profile
                if user_profile.type != 'business':
                    return Response(
                        {'error': 'Authentifizierter Benutzer ist kein \'business\' Profil'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Authentifizierter Benutzer ist kein \'business\' Profil'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate request data
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate 3 details requirement
            details = request.data.get('details', [])
            if len(details) != 3:
                return Response(
                    {'error': 'Ein Offer muss 3 Details enthalten!'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate offer types
            offer_types = [detail.get('offer_type') for detail in details]
            required_types = {'basic', 'standard', 'premium'}
            provided_types = set(offer_types)
            
            if provided_types != required_types:
                return Response(
                    {'error': f'Ungültige Anfragedaten oder unvollständige Details. Benötigt: basic, standard, premium. Erhalten: {list(provided_types)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the offer
            offer = serializer.save(creator=request.user)
            self.create_offer_details_from_request(offer, request.data)
            BaseInfo.update_stats()
            
            # Return 201 Created with the created object (use OfferWithDetailsSerializer for full response)
            response_serializer = OfferWithDetailsSerializer(offer)
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """PATCH /api/offers/{id}/ - Return 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            try:
                instance = self.get_object()
            except Http404:
                return Response(
                    {'error': 'Das Angebot mit der angegebenen ID wurde nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check ownership
            if instance.creator != request.user:
                return Response(
                    {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer des Angebots'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate request data
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate 3 details if details are provided
            details_data = request.data.get('details', [])
            if details_data and len(details_data) != 3:
                return Response(
                    {'error': 'Ein Offer muss 3 Details enthalten!'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            offer = serializer.save()
            if details_data:
                self.update_offer_details(offer, details_data)
            
            # Return full offer with details as per documentation
            response_serializer = OfferWithDetailsSerializer(offer)
            return Response(
                response_serializer.data, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /api/offers/{id}/ - Return 204 No Content, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            try:
                instance = self.get_object()
            except Http404:
                return Response(
                    {'error': 'Das Angebot mit der angegebenen ID wurde nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check ownership
            if instance.creator != request.user:
                return Response(
                    {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer des Angebots'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            instance.delete()
            BaseInfo.update_stats()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        """Enhanced queryset with proper error handling"""
        try:
            queryset = super().get_queryset()
            
            # Handle creator_id filter
            creator_id = self.request.query_params.get('creator_id')
            if creator_id:
                try:
                    creator_id = int(creator_id)
                    queryset = queryset.filter(creator_id=creator_id)
                except ValueError:
                    raise ValidationError({'creator_id': 'Must be a valid integer'})

            # Handle max_delivery_time filter
            max_delivery_time = self.request.query_params.get('max_delivery_time')
            if max_delivery_time:
                try:
                    max_days = int(max_delivery_time)
                    if max_days < 0:
                        raise ValidationError({'max_delivery_time': 'Must be a positive integer'})
                    queryset = queryset.filter(details__delivery_time_in_days__lte=max_days).distinct()
                except ValueError:
                    raise ValidationError({'max_delivery_time': 'Must be a valid integer'})
            
            # Handle min_price filter
            min_price = self.request.query_params.get('min_price')
            if min_price:
                try:
                    min_price_value = float(min_price)
                    if min_price_value < 0:
                        raise ValidationError({'min_price': 'Must be a positive number'})
                    queryset = queryset.filter(details__price__gte=min_price_value).distinct()
                except ValueError:
                    raise ValidationError({'min_price': 'Must be a valid number'})
            
            return queryset
        except ValidationError:
            raise  # Re-raise validation errors to be handled by list method
        except Exception as e:
            raise ValidationError({'error': 'Invalid query parameters'})
    
    def update_offer_details(self, offer, details_data):
        """Update offer details - helper method"""
        for detail_data in details_data:
            detail_id = detail_data.get('id')
            if detail_id:
                try:
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
                except OfferDetail.DoesNotExist:
                    raise ValidationError(f'Offer detail with ID {detail_id} not found')
    
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
                for feature_description in features_list:
                    if feature_description.strip():
                        Feature.objects.create(
                            offer_detail=detail,
                            description=feature_description.strip()
                        )
            except Exception as e:
                raise ValidationError(f"Error creating offer detail: {str(e)}")


class OfferDetailViewSet(viewsets.ModelViewSet):
    """
    API endpoint for offer details with full CRUD operations
    
    NOTE: Documentation only shows GET /api/offerdetails/{id}/ but keeping
    existing CRUD functionality for consistency with original implementation
    """
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailSerializer
    permission_classes = [IsOwnerOrReadOnly]
    
    def retrieve(self, request, *args, **kwargs):
        """GET /api/offerdetails/{id}/ - Return 200 OK, 404 Not Found, 500 Internal Server Error"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(
                {'error': 'Das Angebotsdetail mit der angegebenen ID wurde nicht gefunden'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """Handle creation of offer details with proper authentication checks"""
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required")

        try:
            user_profile = self.request.user.profile
            if user_profile.type != 'business':
                raise PermissionDenied("Only business users can create offer details")
        except Profile.DoesNotExist:
            raise PermissionDenied("User profile not found")
        
        # Make sure the offer belongs to the authenticated user
        offer = serializer.validated_data.get('offer')
        if offer and offer.creator != self.request.user:
            raise PermissionDenied("You can only create details for your own offers")
            
        serializer.save()
    
    def perform_update(self, serializer):
        """Handle updating of offer details with ownership checks"""
        # Check if the user owns the offer that this detail belongs to
        offer_detail = serializer.instance
        if offer_detail.offer.creator != self.request.user:
            raise PermissionDenied("You can only update details of your own offers")
            
        serializer.save()
    
    def perform_destroy(self, instance):
        """Handle deletion of offer details with ownership checks"""
        if instance.offer.creator != self.request.user:
            raise PermissionDenied("You can only delete details of your own offers")
            
        instance.delete()


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
    
    def list(self, request, *args, **kwargs):
        """GET /api/orders/ - Return 200 OK, 401 Unauthorized, 500 Internal Server Error"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """POST /api/orders/ - Return 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user is customer
            try:
                user_profile = request.user.profile
                if user_profile.type != 'customer':
                    return Response(
                        {'error': 'Benutzer hat keine Berechtigung, z.B. weil nicht vom typ \'customer\''}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Benutzer hat keine Berechtigung, z.B. weil nicht vom typ \'customer\''}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate offer_detail_id
            offer_detail_id = request.data.get('offer_detail_id')
            if not offer_detail_id:
                return Response(
                    {'error': 'Ungültige Anfragedaten (z. B. wenn \'offer_detail_id\' fehlt oder ungültig ist)'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                offer_detail = OfferDetail.objects.get(id=offer_detail_id)
            except OfferDetail.DoesNotExist:
                return Response(
                    {'error': 'Das angegebene Angebotsdetail wurde nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create order
            business_user = offer_detail.offer.creator
            order = Order.objects.create(
                customer=request.user,
                business_user=business_user,
                offer_detail=offer_detail,
                status='in_progress'
            )
            
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/orders/{id}/ - Return 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get order
            try:
                order = self.get_object()
            except Http404:
                return Response(
                    {'error': 'Die angegebene Bestellung wurde nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if user is business user and is the assigned business user for this order
            try:
                user_profile = request.user.profile
                if user_profile.type != 'business' or request.user != order.business_user:
                    return Response(
                        {'error': 'Benutzer hat keine Berechtigung, diese Bestellung zu aktualisieren'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Benutzer hat keine Berechtigung, diese Bestellung zu aktualisieren'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate status field
            new_status = request.data.get('status')
            if not new_status:
                return Response(
                    {'error': 'Ungültiger Status oder unzulässige Felder in der Anfrage'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            valid_statuses = ['in_progress', 'completed', 'cancelled']
            if new_status not in valid_statuses:
                return Response(
                    {'error': 'Ungültiger Status oder unzulässige Felder in der Anfrage'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update order
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Update stats if order was completed
            if old_status != 'completed' and new_status == 'completed':
                BaseInfo.update_stats()
            
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_permissions(self):
        """Override permissions for custom actions"""
        if self.action in ['order_count', 'completed_order_count']:
            return [] 
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/orders/{id}/ - Return 204 No Content, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user is staff/admin
            if not request.user.is_staff:
                return Response(
                    {'error': 'Benutzer hat keine Berechtigung, die Bestellung zu löschen'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get and delete order
            try:
                order = self.get_object()
                order.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Http404:
                return Response(
                    {'error': 'Die angegebene Bestellung wurde nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['GET'], url_path='order-count/(?P<business_user_id>[^/.]+)', permission_classes=[AllowAny])
    def order_count(self, request, business_user_id=None):
        """
        GET /api/order-count/{business_user_id}/ - Count in-progress orders for a business user
        NO AUTH REQUIRED - Not in documentation, so can be public
        """
        try:
            # Validate business_user_id
            if not business_user_id:
                return Response(
                    {'error': 'business_user_id ist erforderlich'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                business_user_id = int(business_user_id)
            except ValueError:
                return Response(
                    {'error': 'Ungültige business_user_id'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if business user exists
            try:
                business_user = User.objects.get(id=business_user_id)
                if business_user.profile.type != 'business':
                    return Response(
                        {'error': 'Der angegebene Benutzer ist kein Business-Benutzer'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Business-Benutzer nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Benutzerprofil nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Count in-progress orders for this business user
            order_count = Order.objects.filter(
                business_user=business_user,
                status='in_progress'
            ).count()
            
            return Response(
                {'order_count': order_count}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'], url_path='completed-order-count/(?P<business_user_id>[^/.]+)', permission_classes=[AllowAny])
    def completed_order_count(self, request, business_user_id=None):
        """
        GET /api/completed-order-count/{business_user_id}/ - Count completed orders for a business user
        NO AUTH REQUIRED - Not in documentation, so can be public
        """
        try:
            # Validate business_user_id
            if not business_user_id:
                return Response(
                    {'error': 'business_user_id ist erforderlich'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                business_user_id = int(business_user_id)
            except ValueError:
                return Response(
                    {'error': 'Ungültige business_user_id'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if business user exists
            try:
                business_user = User.objects.get(id=business_user_id)
                if business_user.profile.type != 'business':
                    return Response(
                        {'error': 'Der angegebene Benutzer ist kein Business-Benutzer'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Business-Benutzer nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Benutzerprofil nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Count completed orders for this business user
            completed_order_count = Order.objects.filter(
                business_user=business_user,
                status='completed'
            ).count()
            
            return Response(
                {'completed_order_count': completed_order_count}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ReviewViewSet(viewsets.ModelViewSet):
    """API endpoint for reviews matching documentation exactly"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['business_user', 'reviewer']
    ordering_fields = ['updated_at', 'rating']  
    
    def get_queryset(self):
        """
        Custom queryset filtering to support documentation parameters:
        - business_user_id: Filter reviews for specific business user
        - reviewer_id: Filter reviews by specific reviewer
        - ordering: Sort by 'updated_at' or 'rating'
        """
        queryset = Review.objects.all()
        
        # Filter by business_user_id
        business_user_id = self.request.query_params.get('business_user_id')
        if business_user_id is not None:
            try:
                business_user_id = int(business_user_id)
                queryset = queryset.filter(business_user_id=business_user_id)
            except ValueError:
                raise ValidationError({'business_user_id': 'Must be a valid integer'})
        
        # Filter by reviewer_id  
        reviewer_id = self.request.query_params.get('reviewer_id')
        if reviewer_id is not None:
            try:
                reviewer_id = int(reviewer_id)
                queryset = queryset.filter(reviewer_id=reviewer_id)
            except ValueError:
                raise ValidationError({'reviewer_id': 'Must be a valid integer'})
        
        # Apply ordering
        ordering = self.request.query_params.get('ordering')
        if ordering:
            if ordering in ['updated_at', '-updated_at', 'rating', '-rating']:
                queryset = queryset.order_by(ordering)
            else:
                raise ValidationError({'ordering': 'Must be "updated_at" or "rating"'})
        else:
            queryset = queryset.order_by('-updated_at')  # Default ordering
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        """GET /api/reviews/ - Return 200 OK, 401 Unauthorized, 500 Internal Server Error"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Der Benutzer muss authentifiziert sein'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e.detail) if hasattr(e, 'detail') else str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """POST /api/reviews/ - Return 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Der Benutzer muss authentifiziert sein'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user has customer profile
            try:
                user_profile = request.user.profile
                if user_profile.type != 'customer':
                    return Response(
                        {'error': 'Der Benutzer muss authentifiziert sein und ein Kundenprofil besitzen'}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Der Benutzer muss authentifiziert sein und ein Kundenprofil besitzen'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Validate request data
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Fehlerhafte Anfrage', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user already has a review for this business user
            business_user_id = request.data.get('business_user')
            if business_user_id:
                existing_review = Review.objects.filter(
                    reviewer=request.user, 
                    business_user_id=business_user_id
                ).first()
                if existing_review:
                    return Response(
                        {'error': 'Ein Benutzer kann nur eine Bewertung pro Geschäftsprofil abgeben'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Create the review
            review = serializer.save(reviewer=request.user)
            BaseInfo.update_stats()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/reviews/{id}/ - Return 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Der Benutzer muss authentifiziert sein'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get review
            try:
                review = self.get_object()
            except Http404:
                return Response(
                    {'error': 'Es wurde keine Bewertung mit der angegebenen ID gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check ownership
            if review.reviewer != request.user:
                return Response(
                    {'error': 'Der Benutzer ist nicht berechtigt, diese Bewertung zu bearbeiten'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Only allow rating and description to be updated
            allowed_fields = {'rating', 'description'}
            provided_fields = set(request.data.keys())
            invalid_fields = provided_fields - allowed_fields
            
            if invalid_fields:
                return Response(
                    {'error': 'Der Anfrage-Body enthält ungültige Daten'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate and update
            serializer = self.get_serializer(review, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Der Anfrage-Body enthält ungültige Daten', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /api/reviews/{id}/ - Return 204 No Content, 401 Unauthorized, 403 Forbidden, 404 Not Found"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Der Benutzer muss authentifiziert sein'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get review
            try:
                review = self.get_object()
            except Http404:
                return Response(
                    {'error': 'Es wurde keine Bewertung mit der angegebenen ID gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check ownership
            if review.reviewer != request.user:
                return Response(
                    {'error': 'Der Benutzer ist nicht berechtigt, diese Bewertung zu löschen'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            review.delete()
            BaseInfo.update_stats()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_permissions(self):
        """Override permissions for custom actions"""
        if self.action in ['business_reviews', 'reviewer_reviews']:
            return [] 
        return super().get_permissions()

    @action(detail=False, methods=['GET'], url_path='business/(?P<business_user_id>[^/.]+)', permission_classes=[AllowAny])
    def business_reviews(self, request, business_user_id=None):
        """
        Get all reviews for a specific business user
        NO AUTH REQUIRED - Not in documentation, so can be public
        Return: 200 OK, 404 Not Found, 400 Bad Request
        """
        try:
            # Validate business_user_id
            if not business_user_id:
                return Response(
                    {'error': 'business_user_id ist erforderlich'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                business_user_id = int(business_user_id)
            except ValueError:
                return Response(
                    {'error': 'Ungültige business_user_id'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if business user exists and is actually a business user
            try:
                business_user = User.objects.get(id=business_user_id)
                if business_user.profile.type != 'business':
                    return Response(
                        {'error': 'Der angegebene Benutzer ist kein Business-Benutzer'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Business-Benutzer nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Benutzerprofil nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get reviews for this business user
            reviews = Review.objects.filter(business_user=business_user)
            serializer = self.get_serializer(reviews, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'], url_path='reviewer/(?P<reviewer_id>[^/.]+)', permission_classes=[])
    def reviewer_reviews(self, request, reviewer_id=None):
        """
        Get all reviews by a specific reviewer
        NO AUTH REQUIRED - Not in documentation, so can be public
        Return: 200 OK, 404 Not Found, 400 Bad Request
        """
        try:
            # Validate reviewer_id
            if not reviewer_id:
                return Response(
                    {'error': 'reviewer_id ist erforderlich'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                reviewer_id = int(reviewer_id)
            except ValueError:
                return Response(
                    {'error': 'Ungültige reviewer_id'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if reviewer exists and is actually a customer user
            try:
                reviewer = User.objects.get(id=reviewer_id)
                if reviewer.profile.type != 'customer':
                    return Response(
                        {'error': 'Der angegebene Benutzer ist kein Customer-Benutzer'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Reviewer nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Benutzerprofil nicht gefunden'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get reviews by this reviewer
            reviews = Review.objects.filter(reviewer=reviewer)
            serializer = self.get_serializer(reviews, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



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
