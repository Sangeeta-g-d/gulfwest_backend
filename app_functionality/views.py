from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Product, Favorite
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from users.models import PromoCode
from .serializers import *
from django.shortcuts import get_object_or_404
from decimal import Decimal
from rest_framework.generics import ListAPIView
from rest_framework import generics, permissions
from django.utils import timezone
from pytz import timezone as pytz_timezone

class ToggleFavoriteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, product_id):
       
        user = request.user
        product = get_object_or_404(Product, id=product_id, is_active=True, deleted=False)
        
        # Check if favorite already exists
        favorite = Favorite.objects.filter(user=user, variant=product).first()
        
        if favorite:
            # If exists, remove it (unfavorite)
            favorite.delete()
            return Response(
                {"status": "removed", "message": "Product removed from favorites"},
                status=status.HTTP_200_OK
            )
        else:
            # If doesn't exist, create it
            favorite = Favorite.objects.create(user=user, variant=product)
            serializer = FavoriteSerializer(favorite)
            return Response(
                {"status": "added", "message": "Product added to favorites", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        
class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        variant = serializer.validated_data['variant']
        quantity = serializer.validated_data.get('quantity', 1)
        
        # Remove stock availability check completely
        # Or keep it as informational only (without blocking)
        
        # Get current quantity in cart (if already exists)
        current_in_cart = 0
        try:
            current_item = CartItem.objects.get(cart=cart, variant=variant)
            current_in_cart = current_item.quantity
        except CartItem.DoesNotExist:
            pass
        
        # Add or update item in cart without stock check
        cart_item, created = CartItem.objects.update_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': current_in_cart + quantity}
        )
        
        return Response(
            {
                "message": "Item added to cart successfully",
                "data": CartItemSerializer(cart_item).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
class UserCartAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemDetailSerializer

    def get_queryset(self):
        # Get or create cart for the authenticated user
        cart, created = Cart.objects.get_or_create(user=self.request.user)

        # Optimize query
        return cart.items.select_related(
            'variant__product__category',
            'variant__selling_unit'
        ).prefetch_related(
            'variant__product__images',
            'variant__product__flash_sales'
        ).all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})

        # Calculate cart summary using accurate effective price
        total_items = sum(item.quantity for item in queryset)

        def calculate_effective_price(item):
            price = float(item.variant.price)
            base_discount = float(item.variant.discount_price or 0.0)
            discounted_price = price - base_discount

            # Fetch active flash sale
            now = timezone.now()
            product = item.variant.product

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

            flash_discount = (discounted_price * float(flash_sale.discount_percentage)) / 100 if flash_sale else 0.0
            effective_price = discounted_price - flash_discount
            return round(effective_price * item.quantity, 2)

        total_price = sum(calculate_effective_price(item) for item in queryset)

        return Response({
            'success': True,
            'cart_items': serializer.data,
            'cart_summary': {
                'total_items': total_items,
                'total_unique_items': queryset.count(),
                'total_price': round(total_price, 2),
            }
        })

class IncreaseCartItemQuantityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, variant_id):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, variant_id=variant_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        # Increase quantity by 1 or by passed amount
        increment = request.data.get('increment_by', 1)
        cart_item.quantity += int(increment)
        cart_item.save()

        return Response({
            "message": "Cart item quantity increased successfully",
        }, status=status.HTTP_200_OK)
    
    
class DecreaseCartItemQuantityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, variant_id):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, variant_id=variant_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        # Decrease quantity
        decrement = int(request.data.get('decrement_by', 1))
        cart_item.quantity -= decrement

        if cart_item.quantity <= 0:
            cart_item.delete()
            return Response({
                "message": "Cart item removed as quantity reached 0"
            }, status=status.HTTP_200_OK)
        else:
            cart_item.save()
            return Response({
                "message": "Cart item quantity decreased successfully",
                "data": CartItemSerializer(cart_item, context={'request': request}).data
            }, status=status.HTTP_200_OK)
    

class RemoveCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, variant_id):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, variant_id=variant_id)
            cart_item.delete()
            return Response({
                "message": "Cart item removed successfully."
            }, status=status.HTTP_200_OK)
        except CartItem.DoesNotExist:
            return Response({
                "error": "Item not found in cart."
            }, status=status.HTTP_404_NOT_FOUND)


class AddAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            # Unset other defaults if this is marked as default
            if serializer.validated_data.get('is_default'):
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

            serializer.save(user=request.user)
            return Response({
                "message": "Address added successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class DeleteAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, address_id):
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.delete()
        return Response({
            "message": "Address deleted successfully"
        }, status=status.HTTP_200_OK)

class UserAddressListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user).order_by('-created_at')
        serializer = AddressSerializer(addresses, many=True)
        return Response({
            "message": "Address list fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class EditAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            address = Address.objects.get(pk=pk, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Address updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CartTotalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            items_data = []
            total_items = 0
            total_price = 0.0
            now = timezone.now()

            for item in cart.items.select_related('variant__product__category', 'variant__selling_unit', 'variant__product').prefetch_related('variant__product__flash_sales', 'variant__product__images').all():
                variant = item.variant
                product = variant.product
                price = float(variant.price)
                base_discount = float(variant.discount_price or 0.0)
                discounted = price - base_discount

                # Get active flash sale (product or category level)
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

                flash_discount = (discounted * float(flash_sale.discount_percentage)) / 100 if flash_sale else 0.0
                effective_price = round(discounted - flash_discount, 2)
                total_item_price = round(effective_price * item.quantity, 2)

                total_items += item.quantity
                total_price += total_item_price

                items_data.append({
                    "variant_id": variant.id,
                    "variant_name": f"{product.display_name} - {variant.selling_quantity} {variant.selling_unit.abbreviation}",
                    "quantity": item.quantity,
                    "unit_price": effective_price,
                    "total_price": total_item_price
                })

            return Response({
                "message": "Cart total fetched successfully",
                "total_items": total_items,
                "total_price": round(total_price, 2),
                "items": items_data
            }, status=status.HTTP_200_OK)

        except Cart.DoesNotExist:
            return Response({
                "message": "Cart not found",
                "total_items": 0,
                "total_price": 0.00,
                "items": []
            }, status=status.HTTP_200_OK)

        
class ApplyCouponAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def calculate_effective_price(self, item):
        price = Decimal(item.variant.price)
        base_discount = Decimal(item.variant.discount_price or 0.0)
        discounted_price = price - base_discount

        now = timezone.now()
        product = item.variant.product

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

        flash_discount = (discounted_price * Decimal(flash_sale.discount_percentage) / 100) if flash_sale else Decimal('0.00')
        effective_price = discounted_price - flash_discount

        return effective_price * item.quantity

    def post(self, request):
        code = request.data.get('promo_code')
        if not code:
            return Response({"error": "Promo code is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            promo = PromoCode.objects.get(code=code.strip().upper())
        except PromoCode.DoesNotExist:
            return Response({"error": "Invalid promo code"}, status=status.HTTP_404_NOT_FOUND)

        if not promo.is_valid(user=request.user):
            return Response({"error": "Promo code is not valid or has expired"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        cart_items = cart.items.select_related('variant__product__category').prefetch_related('variant__product__flash_sales')
        cart_total = sum(self.calculate_effective_price(item) for item in cart_items)

        if cart_total < promo.minimum_order_amount:
            return Response({
                "error": f"Minimum order amount ₹{promo.minimum_order_amount} required to use this promo"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate discount
        if promo.discount_type == 'percentage':
            discount = (promo.discount_value / Decimal('100')) * cart_total
        else:
            discount = Decimal(promo.discount_value)

        discount = min(discount, cart_total)
        new_total = cart_total - discount

        return Response({
            "message": "Promo code applied successfully",
            "promo_code": promo.code,
            "original_total": float(round(cart_total, 2)),
            "discount": float(round(discount, 2)),
            "new_total": float(round(new_total, 2)),
        }, status=status.HTTP_200_OK)
    

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
class UserOrderHistoryAPIView(generics.ListAPIView):
    serializer_class = OrderHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-placed_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request  # for image URLs
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Split orders by status
        active_statuses = ['pending', 'confirmed', 'shipped']
        completed_statuses = ['delivered', 'cancelled']

        active_orders = queryset.filter(status__in=active_statuses)
        completed_orders = queryset.filter(status__in=completed_statuses)

        active_serialized = self.get_serializer(active_orders, many=True).data
        completed_serialized = self.get_serializer(completed_orders, many=True).data

        return Response({
            "active": active_serialized,
            "completed": completed_serialized
        })


class ActivePromoCodeListAPIView(generics.ListAPIView):
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        ist = pytz_timezone("Asia/Kolkata")
        now_ist = timezone.now().astimezone(ist)

        valid_promos = []
        for promo in PromoCode.objects.filter(is_active=True):
            if promo.is_valid(user):
                valid_promos.append(promo.id)

        return PromoCode.objects.filter(id__in=valid_promos)
    


class ActiveFlashSaleAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        now = timezone.now()
        active_sales = FlashSale.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).prefetch_related('categories', 'products')

        serializer = FlashSaleSerializer(active_sales, many=True, context={'request': request})
        return Response(serializer.data)
    

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ReorderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        added_items = []

        existing_variant_ids = set(cart.items.values_list('variant_id', flat=True))

        for item in order.items.all():
            if not item.variant:
                continue  # skip if variant no longer exists

            if item.variant.id in existing_variant_ids:
                continue  # skip if already in cart

            cart_item = CartItem.objects.create(
                cart=cart,
                variant=item.variant,
                quantity=item.quantity
            )

            added_items.append({
                "variant_id": item.variant.id,
                "product_name": item.variant.product.display_name,
                "quantity": cart_item.quantity
            })

        return Response({
            "message": "Order re-added to cart (skipping items already present).",
            "items_added": added_items
        }, status=status.HTTP_200_OK)
