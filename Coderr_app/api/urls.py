from django.urls import path, include
from rest_framework.routers import DefaultRouter
from user_auth_app.api import urls as user_auth_urls
from . import views

router = DefaultRouter()
router.register(r"offers", views.OfferViewSet, basename="offer")
router.register(r"offerdetails", views.OfferDetailViewSet, basename="offer-detail")
router.register(r"orders", views.OrderViewSet, basename="order")
router.register(r"reviews", views.ReviewViewSet, basename="review")

urlpatterns = [
    path("", include(user_auth_urls)),
    path("base-info/", views.base_info_view, name="base-info"),
    path(
        "order-count/<int:business_user_id>/",
        views.order_count_proxy,
        name="order-count-proxy",
    ),
    path(
        "completed-order-count/<int:business_user_id>/",
        views.completed_order_count_proxy,
        name="completed-order-count-proxy",
    ),
    path("", include(router.urls)),
]
