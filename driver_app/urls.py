from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('orders/', DriverOrderListAPIView.as_view(), name='driver-orders'),
    path('order-details/<int:order_id>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('update-order-status/<int:order_id>/', MarkOrderDeliveredAPIView.as_view(), name='mark-order-delivered'),
    path('order-history/', DriverOrderHistoryAPIView.as_view(), name='driver-order-history'),
    path('driver-stats/', DriverStatisticsAPIView.as_view(), name='driver_stats'),
]
