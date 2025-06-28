from django.db import models
from django.conf import settings
from django.utils import timezone

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('cash_on_delivery', 'Cash on Delivery'),
        ('pos', 'POS'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey('app_functionality.Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    promo_code = models.ForeignKey('users.PromoCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    original_total = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=29, choices=PAYMENT_CHOICES, default="POS")
    placed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Order #{self.id} by {self.user}"

    def get_status_display_colored(self):
        color_map = {
            'pending': 'secondary',
            'confirmed': 'info',
            'shipped': 'warning',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return f'<span class="badge badge-{color_map[self.status]}">{self.get_status_display()}</span>'
  

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('users.ProductVariant', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()

    price = models.DecimalField(max_digits=10, decimal_places=2)  # unit price at time of order
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # quantity * price

    def __str__(self):
        return f"{self.quantity} x {self.variant} in Order #{self.order.id}"
