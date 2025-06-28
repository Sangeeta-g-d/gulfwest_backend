# utils.py

from decimal import Decimal
from django.utils import timezone
from users.models import FlashSale


def calculate_effective_price(variant):
    """
    Returns the final price for a variant after applying:
    - discount_price
    - flash sale (product-level or category-level)
    """
    now = timezone.now()

    base_price = Decimal(variant.price)
    base_discount = Decimal(variant.discount_price or 0)
    discounted = base_price - base_discount

    # Check flash sale
    product = variant.product
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

    flash_discount = Decimal('0')
    if flash_sale:
        flash_discount = (discounted * Decimal(flash_sale.discount_percentage)) / 100

    effective = discounted - flash_discount
    return round(effective, 2)
