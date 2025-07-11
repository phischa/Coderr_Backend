import traceback
import django_filters
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from django.db import IntegrityError
from django.http import Http404
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError, ParseError
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    AllowAny,
)
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from user_auth_app.models import Profile
from Coderr_app.models import Offer, OfferDetail, Feature, Order, Review, BaseInfo
from .serializers import (
    OfferSerializer,
    OfferWithDetailsSerializer,
    OfferDetailSerializer,
    ReviewSerializer,
    OrderSerializer,
    BaseInfoSerializer,
)
from .permissions import (
    IsBusinessUser,
    IsCustomerUser,
    IsOwnerOrReadOnly,
    OfferDetailPermission,
)


@api_view(["GET"])
def base_info_view(request):
    """
    GET /api/base-info/
    No Permissions required
    """
    try:
        # Update stats to ensure we have current data
        info = BaseInfo.update_stats()

        # Calculate business profile count in real-time for accuracy
        business_profile_count = Profile.objects.filter(type="business").count()

        # Calculate average rating based on all reviews, rounded to 1 decimal place
        avg_rating = Review.objects.aggregate(Avg("rating"))
        average_rating = (
            round(avg_rating["rating__avg"], 1)
            if avg_rating["rating__avg"] is not None
            else 0.0
        )

        # Format response exactly as per documentation
        formatted_data = {
            "review_count": info.total_reviews,
            "average_rating": average_rating,
            "business_profile_count": business_profile_count,
            "offer_count": info.total_offers,
        }

        return Response(formatted_data, status=status.HTTP_200_OK)

    except Exception as e:
        # Handle any internal server errors
        return Response(
            {"error": "Interner Serverfehler"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class DynamicPageNumberPagination(PageNumberPagination):
    """
    Custom pagination that allows page_size to be set via query parameter
    as mentioned in the documentation
    """
    page_size = 6  # Default aus settings.py
    page_size_query_param = 'page_size'
    max_page_size = 100


class OfferFilter(django_filters.FilterSet):
    """Custom filter to map creator_id to creator field with proper error handling"""
    creator_id = django_filters.NumberFilter(field_name='creator', lookup_expr='exact')
    
    def filter_queryset(self, queryset):
        """Override to handle empty creator_id properly"""
        # Get creator_id parameter
        creator_id = self.data.get('creator_id')
        
        # Skip filtering if creator_id is empty/None
        if creator_id is None or creator_id == '' or creator_id == 'null':
            # Remove creator_id from data to prevent errors
            data = self.data.copy()
            data.pop('creator_id', None)
            self.data = data
        
        return super().filter_queryset(queryset)
    
    class Meta:
        model = Offer
        fields = []


class OfferViewSet(viewsets.ModelViewSet):
    """API endpoint for offers with proper status codes and permissions"""
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [IsOwnerOrReadOnly]
    pagination_class = DynamicPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at'] 
    
    def get_queryset(self):
        """Enhanced queryset with proper error handling for all parameters"""
        try:
            queryset = super().get_queryset()
            
            # Handle creator_id filter manually (better error handling)
            creator_id = self.request.query_params.get('creator_id')
            if creator_id and creator_id.strip():  # Only if not empty
                try:
                    creator_id_int = int(creator_id)
                    queryset = queryset.filter(creator_id=creator_id_int)
                except ValueError:
                    # Log but don't crash - just ignore invalid creator_id
                    pass
            
            # Handle max_delivery_time filter
            max_delivery_time = self.request.query_params.get('max_delivery_time')
            if max_delivery_time:
                try:
                    max_days = int(max_delivery_time)
                    if max_days >= 0:  # Allow 0
                        queryset = queryset.filter(details__delivery_time_in_days__lte=max_days).distinct()
                except ValueError:
                    return Response(
                        {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': serializer.errors}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Handle min_price filter
            min_price = self.request.query_params.get('min_price')
            if min_price:
                try:
                    min_price_value = float(min_price)
                    if min_price_value >= 0:  # Allow 0
                        queryset = queryset.filter(details__price__gte=min_price_value).distinct()
                except ValueError:
                    return Response(
                        {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': serializer.errors}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Handle custom ordering for min_price since it's a property
            ordering = self.request.query_params.get('ordering')
            if ordering == 'min_price' or ordering == '-min_price':
                # Custom ordering by min_price (requires annotation)
                from django.db.models import Min, Case, When, Value, DecimalField
                queryset = queryset.annotate(
                    min_price_db=Case(
                        When(details__isnull=True, then=Value(0.0)),
                        default=Min('details__price'),
                        output_field=DecimalField(max_digits=10, decimal_places=2)
                    )
                )
                if ordering == 'min_price':
                    queryset = queryset.order_by('min_price_db')
                else:  # -min_price
                    queryset = queryset.order_by('-min_price_db')
            
            return queryset
            
        except Exception as e:
            # Fallback: return base queryset if anything goes wrong
            return super().get_queryset()
    
    def validate_query_parameters(self, request):
        """Enhanced validation that doesn't crash on invalid params"""
        errors = {}
        
        # creator_id validation
        creator_id = request.query_params.get('creator_id')
        if creator_id and creator_id.strip():  # Only validate if not empty
            try:
                int(creator_id)
            except ValueError:
                errors['creator_id'] = 'Must be a valid integer'
        
        # min_price validation
        min_price = request.query_params.get('min_price')
        if min_price:
            try:
                price = float(min_price)
                if price < 0:
                    errors['min_price'] = 'Must be a positive number'
            except ValueError:
                errors['min_price'] = 'Must be a valid number'
        
        # max_delivery_time validation
        max_delivery_time = request.query_params.get('max_delivery_time')
        if max_delivery_time:
            try:
                days = int(max_delivery_time)
                if days < 0:
                    errors['max_delivery_time'] = 'Must be a positive integer'
            except ValueError:
                errors['max_delivery_time'] = 'Must be a valid integer'
        
        # ordering validation
        ordering = request.query_params.get('ordering')
        if ordering:
            valid_ordering = ['created_at', '-created_at', 'updated_at', '-updated_at', 
                            'min_price', '-min_price']  # min_price handled specially
            if ordering not in valid_ordering:
                errors['ordering'] = f'Must be one of: {", ".join(valid_ordering)}'
        
        if errors:
            raise ValidationError(errors)
    
    def list(self, request, *args, **kwargs):
        """GET /api/offers/ - Enhanced error handling"""
        try:
            # Validate query parameters (but don't crash on invalid ones)
            try:
                self.validate_query_parameters(request)
            except ValidationError as e:
                # Log validation errors but continue with filtered results
                # This prevents crashes from bad frontend requests
                pass
            
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Log the actual error for debugging
            import traceback
            print(f"Error in OfferViewSet.list: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            print(f"Query params: {request.query_params}")
            
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        """
        POST /api/offers/ - Create new offer with 3 details
        
        Status Codes:
        - 201: Das Angebot wurde erfolgreich erstellt
        - 400: Ungültige Anfragedaten oder unvollständige Details
        - 401: Benutzer ist nicht authentifiziert
        - 403: Authentifizierter Benutzer ist kein 'business' Profil
        - 500: Interner Serverfehler
        """
        try:
            # Check authentication first
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check business user permission
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
            
            # Prepare and sanitize data
            data = request.data.copy()
            
            # Handle image field - remove if null/empty as per documentation
            image = data.get('image')
            if image is None or image == '' or image == 'null' or image == 'undefined':
                data.pop('image', None)
            
            # Ensure basic offer fields have defaults
            data['title'] = data.get('title', '').strip()
            data['description'] = data.get('description', '').strip()
            
            # Handle details data - ensure we have all three types with proper defaults
            details_data = data.get('details', [])
            
            # Create default details structure if missing or incomplete
            default_details = {
                'basic': {'offer_type': 'basic', 'title': '', 'revisions': 1, 'delivery_time_in_days': 1, 'price': 0.0, 'features': []},
                'standard': {'offer_type': 'standard', 'title': '', 'revisions': 1, 'delivery_time_in_days': 1, 'price': 0.0, 'features': []},
                'premium': {'offer_type': 'premium', 'title': '', 'revisions': 1, 'delivery_time_in_days': 1, 'price': 0.0, 'features': []}
            }
            
            # Sanitize provided details and fill in missing types
            sanitized_details = []
            provided_types = set()
            
            for detail in details_data:
                offer_type = detail.get('offer_type', 'basic')
                provided_types.add(offer_type)
                
                # Sanitize the detail data to prevent null values
                sanitized_detail = {
                    'offer_type': offer_type,
                    'title': str(detail.get('title', '')).strip(),
                    'revisions': self._sanitize_revisions(detail.get('revisions')),
                    'delivery_time_in_days': self._sanitize_delivery_time(detail.get('delivery_time_in_days')),
                    'price': self._sanitize_price(detail.get('price')),
                    'features': detail.get('features', []) if isinstance(detail.get('features'), list) else []
                }
                sanitized_details.append(sanitized_detail)
            
            # Add missing detail types with defaults
            for detail_type in ['basic', 'standard', 'premium']:
                if detail_type not in provided_types:
                    sanitized_details.append(default_details[detail_type])
            
            # Remove details from offer data (we'll handle them separately)
            offer_data = {k: v for k, v in data.items() if k not in ['details', 'details_data']}
            
            # Use OfferSerializer for creation (without details)
            serializer = OfferSerializer(data=offer_data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the offer
            offer = serializer.save(creator=request.user)
            
            try:
                # Create OfferDetail objects and their features
                for detail_data in sanitized_details:
                    # Create the OfferDetail
                    offer_detail = OfferDetail.objects.create(
                        offer=offer,
                        offer_type=detail_data['offer_type'],
                        title=detail_data['title'],
                        revisions=detail_data['revisions'],
                        delivery_time_in_days=detail_data['delivery_time_in_days'],
                        price=detail_data['price']
                    )
                    
                    # Create the features for this detail
                    features = detail_data.get('features', [])
                    for feature_description in features:
                        if feature_description and str(feature_description).strip():
                            Feature.objects.create(
                                offer_detail=offer_detail,
                                description=str(feature_description).strip()
                            )
            except Exception as e:
                # If detail creation fails, delete the offer and return error
                offer.delete()
                return Response(
                    {'error': 'Fehler beim Erstellen der Details', 'details': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update stats
            BaseInfo.update_stats()
            
            # Return 201 Created with OfferWithDetailsSerializer format
            response_serializer = OfferWithDetailsSerializer(offer)
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        except ParseError:
            # Handle malformed JSON
            return Response(
                {'error': 'Ungültige Anfragedaten oder unvollständige Details'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Profile.DoesNotExist:
            return Response(
                {'error': 'Authentifizierter Benutzer ist kein \'business\' Profil'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _create_offer_details(self, offer, details_data):
        """
        Helper method to create OfferDetail objects and their features.
        This was the missing piece!
        """
        for detail_data in details_data:
            # Create the OfferDetail
            offer_detail = OfferDetail.objects.create(
                offer=offer,
                offer_type=detail_data['offer_type'],
                title=detail_data['title'],
                revisions=detail_data['revisions'],
                delivery_time_in_days=detail_data['delivery_time_in_days'],
                price=detail_data['price']
            )
            
            # Create the features for this detail
            features = detail_data.get('features', [])
            for feature_description in features:
                if feature_description and str(feature_description).strip():
                    Feature.objects.create(
                        offer_detail=offer_detail,
                        description=str(feature_description).strip()
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
            
            # Check ownership (redundant but explicit)
            if instance.creator != request.user:
                return Response(
                    {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer des Angebots'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Separate Behandlung von Offer-Feldern und Details
            data = request.data.copy()
            
            # Extrahiere Details separat (falls vorhanden)
            details_data = data.pop('details', None)
            
            # Validate request data (nur Offer-Felder, OHNE details)
            serializer = self.get_serializer(instance, data=data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update das Offer-Objekt (title, description, etc.)
            offer = serializer.save()
            
            # Update Details falls vorhanden
            if details_data is not None:
                try:
                    self.update_offer_details(offer, details_data)
                except Exception as e:
                    return Response(
                        {'error': 'Fehler beim Aktualisieren der Details', 'details': str(e)}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Load fresh data from database to avoid any caching issues
            fresh_offer = Offer.objects.get(id=offer.id)
            
            # Use the fresh offer for response
            response_serializer = OfferWithDetailsSerializer(fresh_offer)
            response_data = response_serializer.data
            
            return Response(
                response_data, 
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                {'error': 'Ungültige Anfragedaten oder unvollständige Details', 'details': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer des Angebots'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except ParseError as e:
            return Response(
                {'error': 'Ungültige Anfragedaten oder unvollständige Details'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _sanitize_revisions(self, value):
        """Sanitize revisions value - ensure it's a valid integer, default to 1"""
        try:
            if value is None:
                return 1
            int_value = int(value)
            # Allow -1 for unlimited revisions, otherwise minimum 1
            return int_value if int_value == -1 else max(1, int_value)
        except (ValueError, TypeError):
            return 1
    
    def _sanitize_delivery_time(self, value):
        """Sanitize delivery time - ensure it's a positive integer, default to 1"""
        try:
            if value is None:
                return 1
            return max(1, int(value))
        except (ValueError, TypeError):
            return 1
    
    def _sanitize_price(self, value):
        """Sanitize price - ensure it's a non-negative number, default to 0.0"""
        try:
            if value is None:
                return 0.0
            return max(0.0, float(value))
        except (ValueError, TypeError):
            return 0.0
    
    
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
            
            instance.delete()
            BaseInfo.update_stats()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionDenied:
            return Response(
                {'error': 'Authentifizierter Benutzer ist nicht der Eigentümer des Angebots'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': 'Interner Serverfehler'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        """Enhanced queryset with proper error handling"""
        try:
            queryset = super().get_queryset()
            
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
    
    def validate_query_parameters(self, request):
        """Validate query parameters as per documentation"""
        # min_price validation
        min_price = request.query_params.get('min_price')
        if min_price:
            try:
                float(min_price)
            except ValueError:
                raise ValidationError({'min_price': 'Must be a valid number'})
        
        # max_delivery_time validation
        max_delivery_time = request.query_params.get('max_delivery_time')
        if max_delivery_time:
            try:
                max_days = int(max_delivery_time)
                if max_days < 0:
                    raise ValidationError({'max_delivery_time': 'Must be a positive integer'})
            except ValueError:
                raise ValidationError({'max_delivery_time': 'Must be a valid integer'})
    
    def update_offer_details(self, offer, details_data):
        """
        Update offer details - enhanced for PATCH operations
        Supports both 'id' and 'offer_type' based updates
        """
        for detail_data in details_data:
            detail_id = detail_data.get('id')
            offer_type = detail_data.get('offer_type')
            
            # Case 1: Update by ID
            if detail_id:
                try:
                    detail = OfferDetail.objects.get(id=detail_id, offer=offer)
                    self._update_single_detail(detail, detail_data)
                except OfferDetail.DoesNotExist:
                    raise ValidationError(f'Offer detail with ID {detail_id} not found')
            
            # Case 2: Update by offer_type (if no ID provided)
            elif offer_type:
                if offer_type not in ['basic', 'standard', 'premium']:
                    raise ValidationError(f'Invalid offer_type: {offer_type}. Must be basic, standard, or premium.')
                
                try:
                    detail = OfferDetail.objects.get(offer=offer, offer_type=offer_type)
                    self._update_single_detail(detail, detail_data)
                except OfferDetail.DoesNotExist:
                    raise ValidationError(f'Offer detail with offer_type "{offer_type}" not found for this offer')
            
            # Case 3: Neither ID nor offer_type provided
            else:
                raise ValidationError('Each detail must have either "id" or "offer_type" specified')

    def _update_single_detail(self, detail, detail_data):
        """Helper method to update a single OfferDetail object"""
        # Update basic fields with validation
        if 'title' in detail_data:
            detail.title = str(detail_data['title']).strip()
        
        if 'price' in detail_data:
            try:
                price = float(detail_data['price'])
                if price < 0:
                    raise ValidationError('Price cannot be negative')
                detail.price = price
            except (ValueError, TypeError):
                raise ValidationError('Price must be a valid number')
        
        if 'delivery_time_in_days' in detail_data:
            try:
                delivery_time = int(detail_data['delivery_time_in_days'])
                if delivery_time < 1:
                    raise ValidationError('Delivery time must be at least 1 day')
                detail.delivery_time_in_days = delivery_time
            except (ValueError, TypeError):
                raise ValidationError('Delivery time must be a valid integer')
        
        if 'revisions' in detail_data:
            try:
                revisions = detail_data['revisions']
                if revisions == -1:
                    detail.revisions = -1  # Unlimited
                else:
                    revisions = int(revisions)
                    if revisions < 1:
                        raise ValidationError('Revisions must be at least 1 or -1 for unlimited')
                    detail.revisions = revisions
            except (ValueError, TypeError):
                raise ValidationError('Revisions must be a valid integer or -1 for unlimited')
        
        detail.save()
        
        # Update features if provided
        if 'features' in detail_data:
            features_list = detail_data['features']
            if not isinstance(features_list, list):
                raise ValidationError('Features must be a list of strings')
            
            # Delete existing features
            detail.features.all().delete()
            
            # Create new features
            for feature_description in features_list:
                if feature_description and str(feature_description).strip():
                    Feature.objects.create(
                        offer_detail=detail,
                        description=str(feature_description).strip()
                    )

class OfferDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving individual offer details.
    
    Only supports GET /api/offerdetails/{id}/
    CRUD operations (POST, PATCH, DELETE) are handled through /api/offers/{id}/
    """
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailSerializer
    permission_classes = [IsAuthenticated]  # No permissions required as per documentation
    
    def get_serializer(self, *args, **kwargs):
        """
        Always exclude 'offer' field to match documentation response format.
        """
        kwargs['exclude_offer'] = True
        return super().get_serializer(*args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/offerdetails/{id}/ 
        
        Status Codes:
        - 200: Das Angebotsdetail wurde erfolgreich abgerufen
        - 401: Benutzer ist nicht authentifiziert  
        - 404: Das Angebotsdetail mit der angegebenen ID wurde nicht gefunden
        - 500: Interner Serverfehler
        """
        try:
            #Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Benutzer ist nicht authentifiziert'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Now try to get the object
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


class OrderViewSet(viewsets.ModelViewSet):
    """API endpoint for orders"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """Filter orders by user type"""
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()

        try:
            profile_type = user.profile.type
        except Profile.DoesNotExist:
            return Order.objects.none()

        if profile_type == "business":
            return Order.objects.filter(business_user=user)
        else:  # 'customer'
            return Order.objects.filter(customer=user)

    def list(self, request, *args, **kwargs):
        """GET /api/orders/ - Return 200 OK, 401 Unauthorized, 500 Internal Server Error"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Benutzer ist nicht authentifiziert"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        """POST /api/orders/ - Return 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Benutzer ist nicht authentifiziert"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Check if user is customer
            try:
                user_profile = request.user.profile
                if user_profile.type != "customer":
                    return Response(
                        {"error": "Benutzer hat keine Berechtigung, z.B. weil nicht vom typ 'customer'"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Benutzer hat keine Berechtigung, z.B. weil nicht vom typ 'customer'"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Validate using serializer (offer_detail_id now required)
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Ungültige Anfragedaten (z. B. wenn 'offer_detail_id' fehlt oder ungültig ist)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get offer detail from validated data
            offer_detail_id = serializer.validated_data['offer_detail_id']
            try:
                offer_detail = OfferDetail.objects.get(id=offer_detail_id)
            except OfferDetail.DoesNotExist:
                return Response(
                    {"error": "Das angegebene Angebotsdetail wurde nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Create order
            business_user = offer_detail.offer.creator
            order = Order.objects.create(
                customer=request.user,
                business_user=business_user,
                offer_detail=offer_detail,
                status="in_progress",
            )

            # Return created order
            response_serializer = self.get_serializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/orders/{id}/ - Return 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Benutzer ist nicht authentifiziert"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Get order
            try:
                order = self.get_object()
            except Http404:
                return Response(
                    {"error": "Die angegebene Bestellung wurde nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if user is business user and is the assigned business user for this order
            try:
                user_profile = request.user.profile
                if user_profile.type != "business" or request.user != order.business_user:
                    return Response(
                        {"error": "Benutzer hat keine Berechtigung, diese Bestellung zu aktualisieren"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Benutzer hat keine Berechtigung, diese Bestellung zu aktualisieren"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Validate status field
            new_status = request.data.get("status")
            if not new_status:
                return Response(
                    {"error": "Ungültiger Status oder unzulässige Felder in der Anfrage"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            valid_statuses = ["in_progress", "completed", "cancelled"]
            if new_status not in valid_statuses:
                return Response(
                    {"error": "Ungültiger Status oder unzulässige Felder in der Anfrage"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check for invalid fields (only 'status' allowed)
            allowed_fields = {"status"}
            provided_fields = set(request.data.keys())
            invalid_fields = provided_fields - allowed_fields

            if invalid_fields:
                return Response(
                    {"error": "Ungültiger Status oder unzulässige Felder in der Anfrage"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update order
            old_status = order.status
            order.status = new_status
            order.save()

            # Update stats if order was completed
            if old_status != "completed" and new_status == "completed":
                BaseInfo.update_stats()

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/orders/{id}/ - Return 204 No Content, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Benutzer ist nicht authentifiziert"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Check if user is staff/admin
            if not request.user.is_staff:
                return Response(
                    {"error": "Benutzer hat keine Berechtigung, die Bestellung zu löschen"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Get and delete order
            try:
                order = self.get_object()
                order.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Http404:
                return Response(
                    {"error": "Die angegebene Bestellung wurde nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['GET'], url_path='order-count/(?P<business_user_id>[^/.]+)')
    def order_count(self, request, business_user_id=None):
        """
        GET /api/orders/order-count/{business_user_id}/ - Count in-progress orders for a business user
        Return: 200 OK, 401 Unauthorized, 404 Not Found, 500 Internal Server Error
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Benutzer ist nicht authentifiziert"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            # Validate business_user_id
            if not business_user_id:
                return Response(
                    {"error": "business_user_id ist erforderlich"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                business_user_id = int(business_user_id)
            except ValueError:
                return Response(
                    {"error": "Ungültige business_user_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if business user exists
            try:
                business_user = User.objects.get(id=business_user_id)
                if business_user.profile.type != "business":
                    return Response(
                        {"error": "Der angegebene Benutzer ist kein Business-Benutzer"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Kein Geschäftsnutzer mit der angegebenen ID gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Benutzerprofil nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Count in-progress orders for this business user
            order_count = Order.objects.filter(
                business_user=business_user, status="in_progress"
            ).count()

            return Response({"order_count": order_count}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['GET'], url_path='completed-order-count/(?P<business_user_id>[^/.]+)')
    def completed_order_count(self, request, business_user_id=None):
        """
        GET /api/orders/completed-order-count/{business_user_id}/ - Count completed orders for a business user
        Return: 200 OK, 401 Unauthorized, 404 Not Found, 500 Internal Server Error
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Benutzer ist nicht authentifiziert"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            # Validate business_user_id
            if not business_user_id:
                return Response(
                    {"error": "business_user_id ist erforderlich"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                business_user_id = int(business_user_id)
            except ValueError:
                return Response(
                    {"error": "Ungültige business_user_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if business user exists
            try:
                business_user = User.objects.get(id=business_user_id)
                if business_user.profile.type != "business":
                    return Response(
                        {"error": "Der angegebene Benutzer ist kein Business-Benutzer"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Kein Geschäftsnutzer mit der angegebenen ID gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Benutzerprofil nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Count completed orders for this business user
            completed_order_count = Order.objects.filter(
                business_user=business_user, status="completed"
            ).count()

            return Response(
                {"completed_order_count": completed_order_count},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReviewViewSet(viewsets.ModelViewSet):
    """API endpoint for reviews - documentation compliant"""

    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["business_user", "reviewer"]
    ordering_fields = ["updated_at", "rating"]

    def get_queryset(self):
        """
        Custom queryset filtering to support documentation parameters:
        - business_user_id: Filter reviews for specific business user
        - reviewer_id: Filter reviews by specific reviewer
        - ordering: Sort by 'updated_at' or 'rating'
        """
        queryset = Review.objects.all()

        # Filter by business_user_id
        business_user_id = self.request.query_params.get("business_user_id")
        if business_user_id is not None:
            try:
                business_user_id = int(business_user_id)
                queryset = queryset.filter(business_user_id=business_user_id)
            except ValueError:
                raise ValidationError({"business_user_id": "Must be a valid integer"})

        # Filter by reviewer_id
        reviewer_id = self.request.query_params.get("reviewer_id")
        if reviewer_id is not None:
            try:
                reviewer_id = int(reviewer_id)
                queryset = queryset.filter(reviewer_id=reviewer_id)
            except ValueError:
                raise ValidationError({"reviewer_id": "Must be a valid integer"})

        # Apply ordering
        ordering = self.request.query_params.get("ordering")
        if ordering:
            if ordering in ["updated_at", "-updated_at", "rating", "-rating"]:
                queryset = queryset.order_by(ordering)
            else:
                raise ValidationError({"ordering": 'Must be "updated_at" or "rating"'})
        else:
            queryset = queryset.order_by("-updated_at")  # Default ordering

        return queryset

    def list(self, request, *args, **kwargs):
        """GET /api/reviews/ - Return 200 OK, 401 Unauthorized, 500 Internal Server Error"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Der Benutzer muss authentifiziert sein"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {"error": str(e.detail) if hasattr(e, "detail") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        """
        POST /api/reviews/ - Create a new review for a business user
        Status Codes: 201, 400, 401, 403, 500
        """
        try:
            # Check if user is authenticated (already handled by permission_classes)
            user = request.user

            # Check if user has a customer profile
            try:
                if not hasattr(user, "profile"):
                    return Response(
                        {"error": "Unauthorized. Der Benutzer muss authentifiziert sein und ein Kundenprofil besitzen."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

                # Check if user is a customer (not business)
                if user.profile.type != "customer":
                    return Response(
                        {"error": "Unauthorized. Der Benutzer muss authentifiziert sein und ein Kundenprofil besitzen."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            except Exception:
                return Response(
                    {"error": "Unauthorized. Der Benutzer muss authentifiziert sein und ein Kundenprofil besitzen."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Get data from request
            data = request.data.copy()

            # Validate business_user exists and is a business user
            business_user_id = data.get("business_user")
            if not business_user_id:
                return Response(
                    {"error": "business_user ist erforderlich"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                business_user = User.objects.get(id=business_user_id)

                if not hasattr(business_user, "profile") or business_user.profile.type != "business":
                    return Response(
                        {"error": "Der angegebene Benutzer ist kein Geschäftsbenutzer"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Geschäftsbenutzer nicht gefunden"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing_review = Review.objects.filter(
                reviewer=user, business_user=business_user
            ).exists()

            if existing_review:
                return Response(
                    {"error": "Fehlerhafte Anfrage. Der Benutzer hat möglicherweise bereits eine Bewertung für das gleiche Geschäftsprofil abgegeben."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create serializer with the data (without reviewer)
            serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                # Save the review with explicit reviewer
                try:
                    serializer.save(reviewer=request.user)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                except IntegrityError:
                    # Falls die DB-Constraint erst hier greift
                    return Response(
                        {"error": "Forbidden. Ein Benutzer kann nur eine Bewertung pro Geschäftsprofil abgeben."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                # Prüfe ob es eine unique constraint violation ist
                error_messages = str(serializer.errors).lower()
                if 'unique' in error_messages or 'already exists' in error_messages:
                    return Response(
                        {"error": "Forbidden. Ein Benutzer kann nur eine Bewertung pro Geschäftsprofil abgeben."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                else:
                    # Andere Validierungsfehler (rating außerhalb 1-5, etc.)
                    return Response(
                        {"error": "Fehlerhafte Anfrage. Der Anfrage-Body enthält ungültige Daten."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        except IntegrityError as e:
            # Handle database constraint violations (e.g., unique constraint)
            return Response(
                {"error": "Forbidden. Ein Benutzer kann nur eine Bewertung pro Geschäftsprofil abgeben."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/reviews/{id}/ - Return 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Unauthorized. Der Benutzer muss authentifiziert sein."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Get review
            try:
                review = self.get_object()
            except Http404:
                return Response(
                    {"error": "Nicht gefunden. Es wurde keine Bewertung mit der angegebenen ID gefunden."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check ownership
            if review.reviewer != request.user:
                return Response(
                    {"error": "Forbidden. Der Benutzer ist nicht berechtigt, diese Bewertung zu bearbeiten."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Only allow rating and description to be updated
            allowed_fields = {"rating", "description"}
            provided_fields = set(request.data.keys())
            invalid_fields = provided_fields - allowed_fields

            if invalid_fields:
                return Response(
                    {"error": "Bad Request. Der Anfrage-Body enthält ungültige Daten."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate and update
            serializer = self.get_serializer(review, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {"error": "Bad Request. Der Anfrage-Body enthält ungültige Daten."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/reviews/{id}/ - Return 204 No Content, 401 Unauthorized, 403 Forbidden, 404 Not Found"""
        try:
            # Check authentication
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Unauthorized. Der Benutzer muss authentifiziert sein."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Get review
            try:
                review = self.get_object()
            except Http404:
                return Response(
                    {"error": "Nicht gefunden. Es wurde keine Bewertung mit der angegebenen ID gefunden."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check ownership
            if review.reviewer != request.user:
                return Response(
                    {"error": "Forbidden. Der Benutzer ist nicht berechtigt, diese Bewertung zu löschen."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            review.delete()
            BaseInfo.update_stats()
            
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['GET'], url_path='business/(?P<business_user_id>[^/.]+)')
    def business_reviews(self, request, business_user_id=None):
        """
        GET /api/reviews/business/{business_user_id}/ - Get all reviews for a specific business user
        NO AUTH REQUIRED - Not in main documentation
        """
        try:
            # Validate business_user_id
            if not business_user_id:
                return Response(
                    {"error": "business_user_id ist erforderlich"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                business_user_id = int(business_user_id)
            except ValueError:
                return Response(
                    {"error": "Ungültige business_user_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if business user exists and is actually a business user
            try:
                business_user = User.objects.get(id=business_user_id)
                if business_user.profile.type != "business":
                    return Response(
                        {"error": "Der angegebene Benutzer ist kein Business-Benutzer"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Business-Benutzer nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Benutzerprofil nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get reviews for this business user
            reviews = Review.objects.filter(business_user=business_user)
            serializer = self.get_serializer(reviews, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['GET'], url_path='reviewer/(?P<reviewer_id>[^/.]+)')
    def reviewer_reviews(self, request, reviewer_id=None):
        """
        GET /api/reviews/reviewer/{reviewer_id}/ - Get all reviews by a specific reviewer
        NO AUTH REQUIRED - Not in main documentation
        """
        try:
            # Validate reviewer_id
            if not reviewer_id:
                return Response(
                    {"error": "reviewer_id ist erforderlich"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                reviewer_id = int(reviewer_id)
            except ValueError:
                return Response(
                    {"error": "Ungültige reviewer_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if reviewer exists and is actually a customer user
            try:
                reviewer = User.objects.get(id=reviewer_id)
                if reviewer.profile.type != "customer":
                    return Response(
                        {"error": "Der angegebene Benutzer ist kein Customer-Benutzer"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Reviewer nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Benutzerprofil nicht gefunden"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get reviews by this reviewer
            reviews = Review.objects.filter(reviewer=reviewer)
            serializer = self.get_serializer(reviews, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Interner Serverfehler"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_permissions(self):
        """Override permissions for custom actions"""
        if self.action in ["business_reviews", "reviewer_reviews"]:
            return [AllowAny()]  # No auth required for these custom endpoints
        return super().get_permissions()

@api_view(['GET'])
def order_count_proxy(request, business_user_id):
    """
    PROXY VIEW for Frontend Compatibility
    Redirects /api/order-count/{business_user_id}/ to OrderViewSet.order_count
    
    Frontend expects: /api/order-count/{business_user_id}/
    Documentation has: /api/orders/order-count/{business_user_id}/
    """
    # ✅ AUTHENTIFIZIERUNG PRÜFEN ZUERST
    if not request.user.is_authenticated:
        return Response(
            {"error": "Benutzer ist nicht authentifiziert"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    
    # Create an OrderViewSet instance
    viewset = OrderViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    viewset.action = 'order_count'
    
    # Call the original order_count action
    return viewset.order_count(request, business_user_id=business_user_id)


@api_view(['GET'])
def completed_order_count_proxy(request, business_user_id):
    """
    PROXY VIEW for Frontend Compatibility
    Redirects /api/completed-order-count/{business_user_id}/ to OrderViewSet.completed_order_count
    
    Frontend expects: /api/completed-order-count/{business_user_id}/
    Documentation has: /api/orders/completed-order-count/{business_user_id}/
    """
    # ✅ AUTHENTIFIZIERUNG PRÜFEN ZUERST
    if not request.user.is_authenticated:
        return Response(
            {"error": "Benutzer ist nicht authentifiziert"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    
    # Create an OrderViewSet instance
    viewset = OrderViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    viewset.action = 'completed_order_count'
    
    # Call the original completed_order_count action
    return viewset.completed_order_count(request, business_user_id=business_user_id)