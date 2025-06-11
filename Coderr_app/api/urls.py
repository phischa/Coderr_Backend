from django.urls import path, include
from rest_framework.routers import DefaultRouter
from user_auth_app.api import urls as user_auth_urls
from . import views

router = DefaultRouter()
router.register(r'offers', views.OfferViewSet, basename='offer')
router.register(r'offerdetails', views.OfferDetailViewSet, basename='offer-detail')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'profiles', views.ProfileViewSet, basename='profile')

urlpatterns = [
    path('', include(user_auth_urls)),
    # Updated to match documentation: business_user_id instead of user_id
    path('order-count/<int:business_user_id>/', views.OrderViewSet.as_view({'get': 'order_count'}), name='order-count'),
    path('completed-order-count/<int:business_user_id>/', views.OrderViewSet.as_view({'get': 'completed_order_count'}), name='completed-order-count'),
    path('reviews/business/<int:business_user_id>/', views.ReviewViewSet.as_view({'get': 'business_reviews'}), name='business-reviews'),
    path('reviews/reviewer/<int:reviewer_id>/', views.ReviewViewSet.as_view({'get': 'reviewer_reviews'}), name='reviewer-reviews'),
    path('base-info/', views.base_info_view, name='base-info'),
    path('', include(router.urls)),
]
