from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
import uuid, random
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.db.models import Avg
from django.utils import timezone
import pytz
from orders.models import Order

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        if not email and not phone_number:
            raise ValueError("Either email or phone number is required")
        if email:
            email = self.normalize_email(email)
            extra_fields['email'] = email
        if phone_number:
            extra_fields['phone_number'] = phone_number

        user = self.model(**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not email:
            raise ValueError("Superusers must have an email")

        return self.create_user(email=email, password=password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)

    name = models.CharField(max_length=255, blank=True, null=True)
    dob = models.DateField(null=True, blank=True)  # Already exists
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], null=True, blank=True)

    zone = models.CharField(max_length=100, null=True, blank=True)
    area = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(max_length=20, default='customer')
    flag = models.BooleanField(default=False)
    city = models.CharField(max_length=200, null=True, blank=True)

    is_phone_verified = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    profile = models.ImageField(upload_to='profile/', blank=True, null=True)
    PROVINCE_CHOICES = [
        ("Riyadh", "Riyadh"),
        ("Makkah", "Makkah"),
        ("Madinah", "Madinah"),
        ("Qassim", "Qassim"),
        ("Eastern Province", "Eastern Province"),
        ("Asir", "Asir"),
        ("Tabuk", "Tabuk"),
        ("Hail", "Hail"),
        ("Northern Borders", "Northern Borders"),
        ("Jizan", "Jizan"),
        ("Najran", "Najran"),
        ("Al-Bahah", "Al-Bahah"),
        ("Al-Jawf", "Al-Jawf"),
    ]

    province = models.CharField(
        max_length=50, choices=PROVINCE_CHOICES, null=True, blank=True
    )
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email if self.email else self.phone_number

class DeviceToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # Changed from 'active' to 'is_active'

    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.token[:20]}"


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Staff(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    full_name = models.CharField(max_length=300)
    designation = models.CharField(max_length=100)
    city = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    
    # Now supports multiple roles dynamically
    roles = models.ManyToManyField(Role, related_name='staff_members')

    def __str__(self):
        return self.full_name

    def get_role_names(self):
        return ", ".join(self.roles.values_list('name', flat=True))
    
class Categories(models.Model):
    category_name = models.CharField(max_length=40)
    background_img = models.ImageField(upload_to='category/', default="background image")
    is_enabled = models.BooleanField(default=True)  # <-- New field

    def __str__(self):
        return self.category_name

    
# 1️⃣ Unit Model (gram, kilogram, litre, piece, etc.)
class Unit(models.Model):
    name = models.CharField(max_length=50)  # e.g., Gram, Kilogram, Litre, Piece
    abbreviation = models.CharField(max_length=10)  # e.g., gm, kg, l, pc
    conversion_factor_to_base = models.DecimalField(
        max_digits=10, decimal_places=4, default=1
    )  
    # Example: 1kg = 1000 grams --> 1000

    def __str__(self):
        return self.name
    
    
class Product(models.Model):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='products')
    display_name = models.CharField(max_length=255)  # e.g., "Rice"
    description = models.TextField(blank=True, null=True)
    brand_name = models.CharField(max_length=300, blank=True, null=True)
    SAP_code = models.CharField(max_length=100, blank=True, null=True, unique=True)

    # Nutritional Info
    calories = models.CharField(max_length=50, blank=True, null=True)
    water = models.CharField(max_length=50, blank=True, null=True)
    carbs = models.CharField(max_length=50, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name
    
    def average_rating(self):
        return self.ratings.aggregate(avg=Avg('rating'))['avg'] or 0.0
    
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    selling_quantity = models.DecimalField(max_digits=10, decimal_places=2)  # e.g., 1, 25
    selling_unit = models.ForeignKey(Unit, on_delete=models.CASCADE)  # e.g., kg

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    available = models.BooleanField(default=True)  # ✅ new field replacing inventory tracking

    def effective_price(self):
        return self.discount_price if self.discount_price else self.price

    def __str__(self):
        return f"{self.product.display_name} - {self.selling_quantity} {self.selling_unit.abbreviation}"


# 4️⃣ Product Image Model (Multiple images per product)
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    
    def __str__(self):
        return f"Image for {self.product.display_name}"

class FlashSale(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=400, blank=True, null=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Enter discount % (e.g. 10 for 10%)"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    # Apply either to selected categories or selected products
    categories = models.ManyToManyField(Categories, blank=True, related_name='flash_sales')
    products = models.ManyToManyField('Product', blank=True, related_name='flash_sales')
    background_image = models.ImageField(upload_to='flash_sale_backgrounds/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.discount_percentage}% off)"

    def is_currently_active(self):
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    def get_applicable_products(self):
        from users.models import Product
        if self.categories.exists():
            return Product.objects.filter(category__in=self.categories.all(), is_active=True, deleted=False)
        return self.products.filter(is_active=True, deleted=False)


class ProductRating(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_ratings')
    rating = models.PositiveSmallIntegerField()  # 1 to 5 only
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')  # each user can rate a product only once

    def __str__(self):
        return f"{self.product.display_name} - {self.rating}/5"
    
class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    minimum_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text="Minimum cart total required to apply this promo"
    )

    usage_limit = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Max total usage allowed for this promo. Leave blank for unlimited."
    )
    per_user_limit = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Max times a single user can use this promo. Leave blank for unlimited."
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, user=None):
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = timezone.now().astimezone(ist)

        promo_start_ist = self.start_time.astimezone(ist)
        promo_end_ist = self.end_time.astimezone(ist)

        print(f"[DEBUG] Current IST time: {now_ist}")
        print(f"[DEBUG] Promo '{self.code}' Start Time (IST): {promo_start_ist}")
        print(f"[DEBUG] Promo '{self.code}' End Time (IST): {promo_end_ist}")
        print(f"[DEBUG] Promo is_active: {self.is_active}")

        if not self.is_active:
            print("[DEBUG] Promo is not active.")
            return False

        if not (promo_start_ist <= now_ist <= promo_end_ist):
            print("[DEBUG] Current IST time is outside promo validity period.")
            return False

        if self.usage_limit is not None and self.usages.count() >= self.usage_limit:
            print("[DEBUG] Global usage limit exceeded.")
            return False

        if user and self.per_user_limit is not None:
            user_usage_count = self.usages.filter(user=user).count()
            if user_usage_count >= self.per_user_limit:
                print("[DEBUG] Per-user usage limit exceeded.")
                return False

        print("[DEBUG] Promo code is valid.")
        return True


class PromoCodeUsage(models.Model):
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('promo_code', 'user', 'used_at')


class OrderDriverAssignment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='driver_assignment')
    driver = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'driver'})
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Driver {self.driver} assigned to Order #{self.order.id}"
    
class OnboardingImage(models.Model):
    image = models.ImageField(upload_to='onboarding/')
    title = models.CharField(max_length=100, blank=True)
    sub_title = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"OnboardingImage {self.id}"
