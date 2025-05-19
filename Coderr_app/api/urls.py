from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# router.register(r'users', UserViewSet, basename='user') 
router.register(r'offers', views.OfferViewSet)
router.register(r'offerdetails', views.OfferDetailViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'business-profiles', views.BusinessProfileViewSet)
router.register(r'customer-profiles', views.CustomerProfileViewSet)
router.register(r'profile', views.ProfileCompatibilityViewSet, basename='profile-compat')

urlpatterns = [
    path('order-count/<int:user_id>/', views.OrderViewSet.as_view({'get': 'order_count'}), name='order-count'),
    path('completed-order-count/<int:user_id>/', views.OrderViewSet.as_view({'get': 'completed_order_count'}), name='completed-order-count'),
    path('base-info/', views.base_info_view, name='base-info'),
    path('profiles/business/', views.ProfileCompatibilityViewSet.as_view({'get': 'business'}), name='business-profiles-list'),
    path('profiles/customer/', views.ProfileCompatibilityViewSet.as_view({'get': 'customer'}), name='customer-profiles-list'),
    path('', include(router.urls)),
]
