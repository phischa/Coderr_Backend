from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# router.register(r'users', UserViewSet, basename='user') 
router.register(r'offers', views.OfferViewSet)
router.register(r'offerdetails', views.OfferDetailViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'reviews', views.ReviewViewSet)

urlpatterns = [
    # path('', include(router.urls)),
    # path('hello/', hello_world, name='hello_world'),
    path('order-count/<int:user_id>/', views.OrderViewSet.as_view({'get': 'order_count'}), name='order-count'),
    path('completed-order-count/<int:user_id>/', views.OrderViewSet.as_view({'get': 'completed_order_count'}), name='completed-order-count'),
    path('base-info/', views.base_info_view, name='base-info'),
    path('', include(router.urls)),
]
