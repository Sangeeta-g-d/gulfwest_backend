from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
import re
from django.contrib.auth import authenticate
from users.models import *
from django.utils import timezone
import pytz
from app_functionality.models import Cart, CartItem
from app_functionality.models import Favorite

class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        pattern = r'^\+91[6-9]\d{9}$'  # Matches +91 followed by 10 digits starting with 6-9
        if not re.match(pattern, value):
            raise serializers.ValidationError("Phone number must be in the format +91XXXXXXXXXX with 10 digits.")
        return value
    
class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp = serializers.CharField()

class CompleteUserRegistrationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs

    def update(self, instance, validated_data):
        instance.name = validated_data.get('full_name')
        instance.email = validated_data.get('email')
        instance.set_password(validated_data.get('password'))
        instance.save()
        return instance
    
class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        if phone_number and password:
            user = authenticate(request=self.context.get('request'),
                                phone_number=phone_number,
                                password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials.")
        else:
            raise serializers.ValidationError("Must include phone number and password.")
        
        attrs['user'] = user
        return attrs
    

class UpdateZoneAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['zone', 'area', 'latitude', 'longitude']

    
class CategorySerializer(serializers.ModelSerializer):
    background_img = serializers.ImageField(use_url=True)

    class Meta:
        model = Categories
        fields = ['id', 'category_name', 'background_img']

    
# product serializer
class ProductWithFirstVariantSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.category_name')
    selling_quantity = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    flash_discount_price = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    total_discount_percentage = serializers.SerializerMethodField()
    product_images = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    in_cart = serializers.SerializerMethodField()
    cart_quantity = serializers.SerializerMethodField()
    variant_id = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'display_name', 'category',
            'product_images',
            'selling_quantity', 'unit',
            'price', 'discount_price',
            'flash_discount_price',
            'effective_price', 'total_discount_percentage','available','is_favorite','in_cart', 'cart_quantity',
            'variant_id'
        ]

    def get_first_variant(self, product):
        return product.variants.first()

    def get_selling_quantity(self, product):
        variant = self.get_first_variant(product)
        return variant.selling_quantity if variant else None

    def get_unit(self, product):
        variant = self.get_first_variant(product)
        return variant.selling_unit.abbreviation if variant and variant.selling_unit else None

    def get_price(self, product):
        variant = self.get_first_variant(product)
        return float(variant.price) if variant else 0.0

    def get_discount_price(self, product):
        variant = self.get_first_variant(product)
        return float(variant.discount_price) if variant and variant.discount_price else 0.0

    def get_flash_sale(self, product):
        now = timezone.now()

        flash_sale = product.flash_sales.filter(
            is_active=True, start_time__lte=now, end_time__gte=now
        ).first()

        if not flash_sale:
            flash_sale = FlashSale.objects.filter(
                categories=product.category,
                is_active=True,
                start_time__lte=now,
                end_time__gte=now
            ).first()

        return flash_sale

    def get_flash_discount_price(self, product):
        variant = self.get_first_variant(product)
        if not variant:
            return 0.0

        price = float(variant.price)
        base_discount = float(variant.discount_price) if variant.discount_price else 0.0
        discounted_price = price - base_discount

        flash_sale = self.get_flash_sale(product)
        if flash_sale:
            flash_discount = (discounted_price * float(flash_sale.discount_percentage)) / 100
            return round(flash_discount, 2)
        return 0.0

    def get_effective_price(self, product):
        variant = self.get_first_variant(product)
        if not variant:
            return 0.0

        price = float(variant.price)
        base_discount = float(variant.discount_price) if variant.discount_price else 0.0
        discounted_price = price - base_discount

        flash_sale = self.get_flash_sale(product)
        if flash_sale:
            flash_discount = (discounted_price * float(flash_sale.discount_percentage)) / 100
            final_price = discounted_price - flash_discount
            return round(final_price, 2)

        return round(discounted_price, 2)

    def get_total_discount_percentage(self, product):
        price = self.get_price(product)
        effective_price = self.get_effective_price(product)

        if price == 0:
            return 0.0

        total_discount = price - effective_price
        percentage = (total_discount / price) * 100
        return round(percentage, 2)

    def get_product_images(self, product):
        request = self.context.get('request')
        return [
            request.build_absolute_uri(img.image.url) if request else img.image.url
            for img in product.images.all()
        ]
    def get_available(self, product):
        variant = self.get_first_variant(product)
        return variant.available if variant else False
    def get_is_favorite(self, product):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(user=request.user, variant=product).exists()
    def get_in_cart(self, product):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        variant = self.get_first_variant(product)
        if not variant:
            return False

        return CartItem.objects.filter(cart__user=request.user, variant=variant).exists()

    def get_cart_quantity(self, product):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0

        variant = self.get_first_variant(product)
        if not variant:
            return 0

        try:
            cart_item = CartItem.objects.get(cart__user=request.user, variant=variant)
            return cart_item.quantity
        except CartItem.DoesNotExist:
            return 0
    def get_variant_id(self, product):
        variant = self.get_first_variant(product)
        return variant.id if variant else None



# product details serializers
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image']

class VariantSerializer(serializers.ModelSerializer):
    unit = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()
    flash_discount_price = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    total_discount_percentage = serializers.SerializerMethodField()
    in_cart = serializers.SerializerMethodField()
    cart_quantity = serializers.SerializerMethodField()
    
    # ✅ Directly serialize the boolean field
    available = serializers.BooleanField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'selling_quantity', 'unit', 'price',
            'discount_price', 'flash_discount_price',
            'effective_price', 'total_discount_percentage',
            'in_cart', 'cart_quantity',
            'available'  # ✅ New field
        ]

    def get_unit(self, variant):
        return variant.selling_unit.abbreviation

    def get_price(self, variant):
        return float(variant.price)

    def get_discount_price(self, variant):
        return float(variant.discount_price or 0.0)

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

    def get_flash_discount_price(self, variant):
        price = float(variant.price)
        discount_price = float(variant.discount_price or 0.0)
        discounted = price - discount_price
        flash_sale = self.get_flash_sale(variant)
        if flash_sale:
            return round(discounted * float(flash_sale.discount_percentage) / 100, 2)
        return 0.0

    def get_effective_price(self, variant):
        price = float(variant.price)
        discount_price = float(variant.discount_price or 0.0)
        discounted = price - discount_price
        flash_discount = self.get_flash_discount_price(variant)
        return round(discounted - flash_discount, 2)

    def get_total_discount_percentage(self, variant):
        price = float(variant.price)
        effective_price = self.get_effective_price(variant)
        if price == 0:
            return 0.0
        return round((price - effective_price) / price * 100, 2)

    def get_in_cart(self, variant):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        cart = getattr(request.user, 'cart', None)
        if not cart:
            return False
        return cart.items.filter(variant=variant).exists()

    def get_cart_quantity(self, variant):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        cart = getattr(request.user, 'cart', None)
        if not cart:
            return 0
        cart_item = cart.items.filter(variant=variant).first()
        return cart_item.quantity if cart_item else 0


    
class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    variants = VariantSerializer(many=True, read_only=True)
    default_variant = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = [
            'id', 'display_name', 'description', 'brand_name',
            'calories', 'water', 'carbs', 'images',
            'average_rating', 'variants', 'default_variant','is_favorite'
        ]

    def get_average_rating(self, obj):
        return obj.average_rating()

    def get_default_variant(self, obj):
        first_variant = obj.variants.first()
        if not first_variant:
            return None
        return VariantSerializer(first_variant, context=self.context).data
    
    def get_is_favorite(self, product):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return product.favorited_by.filter(user=request.user).exists()

class ProductSimpleSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'display_name', 'image', 'price', 'effective_price']

    def get_image(self, obj):
        request = self.context.get('request')
        first_image = obj.images.first()
        if first_image and first_image.image:
            if request:
                # This will build the absolute URL including scheme and domain
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

    def get_variant(self, obj):
        return obj.variants.first()

    def get_price(self, obj):
        variant = self.get_variant(obj)
        return float(variant.price) if variant else 0.0

    def get_effective_price(self, obj):
        variant = self.get_variant(obj)
        if not variant:
            return 0.0
        return float(variant.discount_price) if variant.discount_price else float(variant.price)


class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating
        fields = ['product', 'rating']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class RecentProductRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductRating
        fields = ['rating', 'user_name']

    def get_user_name(self, obj):
        return obj.user.name or obj.user.email or obj.user.phone_number
    

class OnboardingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingImage
        fields = ['id', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
