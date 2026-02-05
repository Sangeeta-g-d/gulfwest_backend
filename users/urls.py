from django.urls import path
from . import views

urlpatterns = [
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('', views.login_view, name='login'),
    path('logout/',views.logout_view,name="logout"),
    path('customers/', views.customers, name='customers'),
    path('toggle-approval/<int:id>/', views.toggle_approval, name='toggle_approval'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('staff_details/',views.staff_details, name='staff_details'),
    path('add_staff/',views.add_staff, name='add_staff'),
    path("privacy/",views.privacy,name="privacy"),
    path("terms/",views.terms,name="terms"),

    path('add_category/', views.add_category, name='add_category'),
    path('category-toggle/<int:category_id>/', views.toggle_category_status, name='toggle_category_status'),
    path('category_list/',views.category_list,name="category_list"),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('add_unit/',views.add_unit,name="add_unit"),
    path('products/', views.products, name='products'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('upload_bulk_products/<int:id>',views.upload_bulk_products, name='upload_bulk_products'),
    
    # product urls  
    path('add_product/', views.add_product_and_variant, name='add_product'),
    path('add-images/<int:product_id>/', views.add_images, name='add_images'),
    path('view_products/', views.view_products, name='view_products'),
    path('products/export/', views.export_products_excel, name='export_products_excel'),

    path('product_details/<int:product_id>/', views.product_details, name='product_details'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('edit_product_image/<int:image_id>/edit/', views.edit_product_image, name='edit_product_image'),
    path('delete_product_image/<int:image_id>/delete/', views.delete_product_image, name='delete_product_image'),
    path('upload_product_image/<int:product_id>/upload-image/', views.upload_product_image, name='upload_product_image'),
    path('delete_product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('edit_variant/<int:variant_id>/', views.edit_variant, name='edit_variant'),
    path('delete_variant/<int:variant_id>/', views.delete_variant, name='delete_variant'),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset-password/<uidb64>/<token>/", views.reset_password_view, name="reset_password"),
    path("delete-account/", views.anonymize_account_view, name="anonymize_account"),


    # staff details
    path('edit_staff_details/<int:staff_id>/', views.edit_staff_details, name='edit_staff_details'),
    path('delete_staff/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('add-role/', views.add_role, name='add_role'),
    path('manage_vat/',views.manage_vat,name="manage_vat"),

    # flash sale
    path('add_flash_sale/',views.add_flash_sale,name="add_flash_sale"),
    path('flash_sale/',views.flash_sale,name="flash_sale"),
    path('edit_flash_sale/<int:sale_id>/', views.edit_flash_sale, name='edit_flash_sale'),
    path('delete_flash_sale/<int:sale_id>/', views.delete_flash_sale, name='delete_flash_sale'),

    # driver
    path('driver/',views.driver,name="driver"),
    path('add_driver/',views.add_driver,name="add_driver"),
    path('edit_driver/<int:driver_id>/',views.edit_driver,name="edit_driver"),
    path('delete_driver/<int:driver_id>/', views.delete_driver, name='delete_driver'),

    # promo code
    path('promo_code/',views.promo_code,name="promo_code"),
    path('add_promo_code/',views.add_promo_code,name="add_promo_code"),
    path('edit_promo_code/<int:promo_id>/', views.edit_promo_code, name='edit_promo_code'),
    path('delete_promo_code/<int:promo_id>/',views.delete_promo_code,name="delete_promo_code"),
    path('promo-usage-chart/', views.promo_usage_chart, name='promo_usage_chart'),

    # orders
    path('orders/',views.orders,name="orders"),
    path('delete-order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('assign-driver/<int:order_id>/', views.assign_driver_to_order, name='assign_driver'),
    path('orders/<int:order_id>/change-status/', views.change_order_status, name='change_order_status'),


    # staff related urls
    path('staff_dashboard/',views.staff_dashboard,name="staff_dashboard"),

    path('onboarding-images/',views.onboarding_images,name="onboarding_images"),
    path('delete_onboarding_image/<int:pk>/', views.delete_onboarding_image, name='delete_onboarding_image'),


    path('manage_banner/', views.manage_banner, name='manage_banner'),
]
