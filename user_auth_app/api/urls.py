from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for our viewsets
router = DefaultRouter()
router.register(r'profiles', views.ProfileViewSet, basename='profile')

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registration/', views.registration_view, name='registration'),
    # Primary endpoint - pk is user_id as per documentation
    path('profile/<int:pk>/', views.ProfileViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='profile-detail'),
    # Alternative endpoint for backward compatibility
    path('profile/user/<int:pk>/', views.ProfileViewSet.as_view({'get': 'get_by_user_id', 'patch': 'get_by_user_id'}), name='profile-by-user'),
    path('profiles/business/', views.ProfileViewSet.as_view({'get': 'business_profiles'}), name='business-profiles'),
    path('profiles/customer/', views.ProfileViewSet.as_view({'get': 'customer_profiles'}), name='customer-profiles'),
    path('', include(router.urls)),
]


