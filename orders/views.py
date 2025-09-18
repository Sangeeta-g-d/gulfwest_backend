# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from users.models import VAT
from decimal import Decimal
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem
from users.models import PromoCode, PromoCodeUsage
from app_functionality.models import Cart
from .serializers import ConfirmOrderSerializer
from .utils.pricing import calculate_effective_price

class ConfirmOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ConfirmOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        cart = getattr(user, 'cart', None)

        if not cart or not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        address_id = data['address_id']
        promo_code_str = data.get('promo_code')
        payment_type = data.get('payment_type', 'POS')

        original_total = Decimal('0')

        for item in cart.items.select_related('variant'):
            variant = item.variant
            price = calculate_effective_price(variant)
            original_total += price * item.quantity

        discount = Decimal('0')
        promo_code = None

        if promo_code_str:
            try:
                promo_code = PromoCode.objects.get(code__iexact=promo_code_str.strip())
                if promo_code.is_valid(user):
                    if promo_code.discount_type == 'percentage':
                        discount = (original_total * promo_code.discount_value) / 100
                    elif promo_code.discount_type == 'fixed':
                        discount = promo_code.discount_value

                    discount = min(discount, original_total)
                else:
                    return Response({'error': 'Promo code is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)
            except PromoCode.DoesNotExist:
                return Response({'error': 'Promo code not found.'}, status=status.HTTP_404_NOT_FOUND)

        final_total = original_total - discount

        # ✅ Fetch VAT value (default 0 if none exists)
        vat = VAT.objects.first()
        vat_percent = vat.value if vat else Decimal('0')
        vat_amount = (final_total * vat_percent) / 100
        total_including_tax = final_total + vat_amount

        # Create order with VAT-inclusive total
        order = Order.objects.create(
            user=user,
            address_id=address_id,
            promo_code=promo_code,
            original_total=original_total,
            discount=discount,
            final_total=final_total,
            total_including_tax=total_including_tax,  # ✅ new field
            payment_type=payment_type,
            placed_at=timezone.now(),
        )

        for item in cart.items.select_related('variant'):
            variant = item.variant
            price = calculate_effective_price(variant)
            OrderItem.objects.create(
                order=order,
                variant=variant,
                quantity=item.quantity,
                price=price,
                total_price=price * item.quantity
            )

        if promo_code:
            PromoCodeUsage.objects.create(user=user, promo_code=promo_code)

        cart.items.all().delete()

        return Response({
            'message': 'Order placed successfully.',
            'order_id': order.id,
            'original_total': str(original_total),
            'discount': str(discount),
            'final_total': str(final_total),
            'vat_percent': str(vat_percent),
            'total_including_tax': str(total_including_tax)
        }, status=status.HTTP_201_CREATED)
    

class CancelOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status != 'pending':
            return Response({
                "detail": "Only orders with status 'pending' can be cancelled."
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'cancelled'
        order.save()

        return Response({
            "message": f"Order #{order.id} has been cancelled successfully."
        }, status=status.HTTP_200_OK)
    

class UserDeleteOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        order.is_deleted_by_user = True
        order.save()
        return Response({"detail": "Order deleted successfully from user view."}, status=status.HTTP_200_OK)