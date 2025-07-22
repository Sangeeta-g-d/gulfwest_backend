from django.urls import path
from .views import *

urlpatterns = [
    path('favorites-toggle/<int:product_id>/', ToggleFavoriteAPIView.as_view(), name='toggle-favorite'),
    path('add-to-cart/', AddToCartAPIView.as_view(), name='add-to-cart'),
    path('cart/', UserCartAPIView.as_view(), name='user-cart'),
    path('increase-item/<int:variant_id>/', IncreaseCartItemQuantityAPIView.as_view(), name='increase-cart-item'),
    path('decrease-item/<int:variant_id>/', DecreaseCartItemQuantityAPIView.as_view(), name='increase-cart-item'),
    path('remove-item/<int:variant_id>/', RemoveCartItemAPIView.as_view(), name='remove-cart-item'),
    path('add-address/', AddAddressAPIView.as_view(), name='add-address'),

    # 16-06-25
    path('edit-address/<int:pk>/', EditAddressAPIView.as_view(), name='edit-address'),
    path('addresses/', UserAddressListAPIView.as_view(), name='user-addresses'),
    path('delete-address/<int:address_id>/', DeleteAddressAPIView.as_view(), name='delete-address'),
    path('checkout/', CartTotalAPIView.as_view(), name='checkout-cart-total'),
    path('apply-coupon/', ApplyCouponAPIView.as_view(), name='apply-coupon'),
    path('account/', UserProfileAPIView.as_view(), name='user-profile'),
    path('order-history/', UserOrderHistoryAPIView.as_view(), name='order-history'),
    path('promo-codes/', ActivePromoCodeListAPIView.as_view(), name='active-promo-codes'),

    # flash sale 19-6-25
    path('flash-sale-info/',ActiveFlashSaleAPIView.as_view(),name="flash-sale"),
    # path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('reorder/<int:order_id>/', ReorderAPIView.as_view(), name='reorder'),


]
