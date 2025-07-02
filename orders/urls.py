from django.urls import path
from .views import *

urlpatterns = [
    path('confirm-order/', ConfirmOrderView.as_view(), name='confirm_order'),
    path('cancel-order/<int:order_id>/', CancelOrderAPIView.as_view(), name='cancel-order'),
    path('delete-order/<int:order_id>/', UserDeleteOrderAPIView.as_view(), name='user-delete-order'),
]