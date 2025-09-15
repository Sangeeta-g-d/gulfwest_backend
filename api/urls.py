from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    
   path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
   path('send-otp/', SendOTPView.as_view(), name='send-otp'),
   path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
   path('complete-registration/', CompleteUserRegistrationView.as_view(), name='complete-registration'),
   path('login/', PhoneLoginView.as_view(), name='phone-login'),
   path('update-zone-area/', UpdateZoneAreaView.as_view(), name='update-zone-area'),
   path('categories/', CategoryListAPIView.as_view(), name='category-list'),
   path('logout/', LogoutAPIView.as_view(), name='logout'),

   # newly added
   path('products/', ProductListWithSingleVariantAPIView.as_view(), name='product-single-variant'),
   path('product/<int:product_id>/', ProductDetailAPIView.as_view(), name='product-detail'),
   path('products-by-category/<int:category_id>/', ProductsByCategoryAPIView.as_view(), name='products_by_category'),
   path('favorite_products/',FavoriteProductListAPIView.as_view(),name="fav-products"),
   path('best-selling-products/', BestSellingProductsAPIView.as_view(), name='best-selling-products'),
   path('rate-product/', AddOrUpdateProductRatingView.as_view(), name='product-rate'),
   path('search-products/', ProductSearchAPIView.as_view(), name='product_search'),

   path('onboarding-images/', OnboardingImageListAPIView.as_view(), name='onboarding_images_api'),
   path("save-device-token/", SaveDeviceTokenAPIView.as_view(), name="save_device_token"),

]

