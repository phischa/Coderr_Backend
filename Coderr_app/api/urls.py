# Aktualisierte urls.py für Coderr_app:

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'offers', views.OfferViewSet, basename='offer')
router.register(r'offerdetails', views.OfferDetailViewSet, basename='offer-detail')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'profiles', views.ProfileViewSet, basename='profile')

urlpatterns = [
    path('order-count/<int:user_id>/', views.OrderViewSet.as_view({'get': 'order_count'}), name='order-count'),
    path('completed-order-count/<int:user_id>/', views.OrderViewSet.as_view({'get': 'completed_order_count'}), name='completed-order-count'),
    path('base-info/', views.base_info_view, name='base-info'),
    path('profiles/business/', views.ProfileViewSet.as_view({'get': 'business'}), name='business-profiles-list'),
    path('profiles/customer/', views.ProfileViewSet.as_view({'get': 'customer'}), name='customer-profiles-list'),
    path('profile/<int:pk>/', views.ProfileViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='profile-detail'),
    path('profile/user/<int:pk>/', views.ProfileViewSet.as_view({'get': 'get_by_user_id', 'patch': 'get_by_user_id'}), name='profile-by-user'),
    path('reviews/business/<int:business_user_id>/', views.ReviewViewSet.as_view({'get': 'business_reviews'}), name='business-reviews'),
    path('reviews/reviewer/<int:reviewer_id>/', views.ReviewViewSet.as_view({'get': 'reviewer_reviews'}), name='reviewer-reviews'),
    path('', include(router.urls)),
]
