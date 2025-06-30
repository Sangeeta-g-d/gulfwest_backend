from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from users.models import PromoCode
from django.utils import timezone
from django.utils.timezone import localtime
from users.models import FlashSale
import pytz
from api.serializers import ProductWithFirstVariantSerializer
User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']

class ProductBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'display_name', 'category']

class FavoriteSerializer(serializers.ModelSerializer):
    variant = ProductBasicSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'variant', 'added_at']
        read_only_fields = ['user', 'added_at']

# add to cart
class AddToCartSerializer(serializers.ModelSerializer):
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),  # Removed status filter
        source='variant'
    )
    
    class Meta:
        model = CartItem
        fields = ['variant_id', 'quantity']
        extra_kwargs = {
            'quantity': {'min_value': 1}
        }

class CartItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.product.display_name', read_only=True)
    unit = serializers.CharField(source='variant.selling_unit.abbreviation', read_only=True)
    price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'variant_id', 'variant_name', 'quantity', 'unit', 'price', 'total_price']
    
    def get_price(self, obj):
        return obj.variant.discount_price if obj.variant.discount_price else obj.variant.price
    
    def get_total_price(self, obj):
        return obj.quantity * (obj.variant.discount_price if obj.variant.discount_price else obj.variant.price)
    
class CartItemDetailSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.product.display_name', read_only=True)
    product_id = serializers.IntegerField(source='variant.product.id', read_only=True)
    category_name = serializers.CharField(source='variant.product.category.category_name', read_only=True)
    unit = serializers.CharField(source='variant.selling_unit.abbreviation', read_only=True)
    selling_quantity = serializers.CharField(source='variant.selling_quantity', read_only=True)
    image = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    flash_discount_price = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'variant_id',
            'product_id',
            'variant_name',
            'category_name',
            'quantity',
            'selling_quantity',
            'unit',
            'price',
            'discount_price',
            'flash_discount_price',
            'effective_price',
            'total_price',
            'image',
            'added_at'
        ]

    def get_price(self, obj):
        return float(obj.variant.price)

    def get_discount_price(self, obj):
        return float(obj.variant.discount_price or 0.0)

    def get_flash_sale(self, variant):
        now = timezone.now()
        product = variant.product

        flash_sale = product.flash_sales.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).first()

        if not flash_sale:
            flash_sale = FlashSale.objects.filter(
                categories=product.category,
                is_active=True,
                start_time__lte=now,
                end_time__gte=now
            ).first()

        return flash_sale

    def get_flash_discount_price(self, obj):
        price = float(obj.variant.price)
        base_discount = float(obj.variant.discount_price or 0.0)
        discounted = price - base_discount

        flash_sale = self.get_flash_sale(obj.variant)
        if flash_sale:
            flash_discount = (discounted * float(flash_sale.discount_percentage)) / 100
            return round(flash_discount, 2)
        return 0.0

    def get_effective_price(self, obj):
        price = float(obj.variant.price)
        base_discount = float(obj.variant.discount_price or 0.0)
        discounted = price - base_discount
        flash_discount = self.get_flash_discount_price(obj)
        return round(discounted - flash_discount, 2)

    def get_total_price(self, obj):
        return float(self.get_effective_price(obj)) * obj.quantity

    def get_image(self, obj):
        image = obj.variant.product.images.first()
        request = self.context.get('request')
        if image:
            return request.build_absolute_uri(image.image.url) if request else image.image.url
        return None


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'name', 'phone_number',
            'address_line1', 'address_line2',
            'city', 'state', 'country', 'pincode','latitude', 'longitude',
            'address_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# order history
class OrderItemShortSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'quantity', 'price', 'total_price', 'product_name', 'product_image']

    def get_product_name(self, obj):
        return obj.variant.product.display_name if obj.variant and obj.variant.product else None

    def get_product_image(self, obj):
        if obj.variant and obj.variant.product:
            image = obj.variant.product.images.first()
            if image:
                request = self.context.get('request')
                return request.build_absolute_uri(image.image.url) if request else image.image.url
        return None


class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemShortSerializer(many=True)
    
    class Meta:
        model = Order
        fields = ['id', 'status', 'placed_at', 'final_total', 'items']



class PromoCodeSerializer(serializers.ModelSerializer):
    start_time_formatted = serializers.SerializerMethodField()
    end_time_formatted = serializers.SerializerMethodField()

    class Meta:
        model = PromoCode
        fields = [
            'code', 'description', 'discount_type', 'discount_value',
            'minimum_order_amount', 'usage_limit', 'per_user_limit',
            'start_time', 'end_time',
            'start_time_formatted', 'end_time_formatted',
        ]

    def get_start_time_formatted(self, obj):
        ist = pytz.timezone("Asia/Kolkata")
        return obj.start_time.astimezone(ist).strftime("%d %B %Y, %I:%M %p")

    def get_end_time_formatted(self, obj):
        ist = pytz.timezone("Asia/Kolkata")
        return obj.end_time.astimezone(ist).strftime("%d %B %Y, %I:%M %p")
    
class FlashSaleSerializer(serializers.ModelSerializer):
    background_image = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = FlashSale
        fields = [
            'id', 'name', 'tagline', 'discount_percentage',
            'start_time', 'end_time',
            'categories',  # can be full or just id & name depending on logic
            'background_image',
            'products',    # product data shown only if flash sale is on products
        ]

    def get_background_image(self, obj):
        request = self.context.get('request')
        if obj.background_image and hasattr(obj.background_image, 'url'):
            return request.build_absolute_uri(obj.background_image.url) if request else obj.background_image.url
        return None

    def get_start_time(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        return localtime(obj.start_time, ist).strftime('%Y-%m-%d %I:%M %p')

    def get_end_time(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        return localtime(obj.end_time, ist).strftime('%Y-%m-%d %I:%M %p')

    def get_categories(self, obj):
        if obj.products.exists():
            return []  # don’t include categories if flash sale is on products
        return [{'id': cat.id, 'name': cat.category_name} for cat in obj.categories.all()]

    def get_products(self, obj):
        if obj.products.exists():
            products_qs = obj.products.filter(is_active=True, deleted=False).prefetch_related(
                'variants', 'images', 'flash_sales'
            )
            return ProductWithFirstVariantSerializer(products_qs, many=True, context=self.context).data
        return []  # don’t include product details if sale is on categories

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'phone_number', 'name', 'dob', 'gender', 'profile']
        read_only_fields = ['email', 'phone_number']
