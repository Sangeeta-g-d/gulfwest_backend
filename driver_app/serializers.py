from rest_framework import serializers
from orders.models import Order,OrderItem
from django.utils.timezone import localtime
from app_functionality.models import Address
import pytz

class DriverOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    placed_at = serializers.SerializerMethodField()
    delivery_name = serializers.SerializerMethodField()
    delivery_phone = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    delivery_city = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'final_total', 'payment_type', 'placed_at', 'customer_name',
            'delivery_name', 'delivery_phone', 'delivery_address', 'delivery_city'
        ]

    def get_customer_name(self, obj):
        return obj.user.name or obj.user.email or obj.user.phone_number

    def get_placed_at(self, obj):
        ist = pytz.timezone("Asia/Kolkata")
        return localtime(obj.placed_at, timezone=ist).strftime("%d-%m-%Y %I:%M %p")

    def get_delivery_name(self, obj):
        return obj.address.name if obj.address else ""

    def get_delivery_phone(self, obj):
        return obj.address.phone_number if obj.address else ""

    def get_delivery_address(self, obj):
        if obj.address:
            line1 = obj.address.address_line1
            line2 = obj.address.address_line2
            return f"{line1}, {line2}" if line2 else line1
        return ""

    def get_delivery_city(self, obj):
        return obj.address.city if obj.address else ""



class OrderItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'variant_name', 'quantity', 'price', 'total_price']

    def get_variant_name(self, obj):
        return str(obj.variant) if obj.variant else "N/A"
    
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'name', 'phone_number', 'address_line1', 'address_line2',
            'city', 'state', 'country', 'pincode', 'latitude', 'longitude', 'address_type'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    customer_name = serializers.SerializerMethodField()
    placed_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'payment_type', 'original_total', 'discount', 'final_total',
            'placed_at', 'customer_name', 'address', 'items'
        ]

    def get_customer_name(self, obj):
        return obj.user.name or obj.user.email or obj.user.phone_number

    def get_placed_at(self, obj):
        ist = pytz.timezone("Asia/Kolkata")
        return localtime(obj.placed_at, timezone=ist).strftime("%d-%m-%Y %I:%M %p")