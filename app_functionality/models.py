from django.db import models
from users.models import CustomUser,Product,ProductVariant
from django.conf import settings
# Create your models here.

class Favorite(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='favorites')
    variant = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='favorited_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'variant') 
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user} → {self.variant}"
    

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def get_total_price(self):
        return sum(
            item.get_item_price() 
            for item in self.items.select_related('variant').all()
        )

    def __str__(self):
        return f"Cart of {self.user.email or self.user.phone_number}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def get_item_price(self):
        if self.variant.discount_price:
            return self.quantity * self.variant.discount_price
        return self.quantity * self.variant.price

    class Meta:
        unique_together = ('cart', 'variant')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.quantity} x {self.variant} in cart"
    

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('Home', 'Home'),
        ('Work', 'Work'),
        ('Other', 'Other'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100, help_text="Recipient name")
    phone_number = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    pincode = models.CharField(max_length=10)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='home')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name}, {self.city} - {self.pincode}"