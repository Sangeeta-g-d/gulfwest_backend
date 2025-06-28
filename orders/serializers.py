# serializers.py

from rest_framework import serializers


class ConfirmOrderSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    promo_code = serializers.CharField(required=False, allow_blank=True)
    payment_type = serializers.ChoiceField(choices=["cash_on_delivery", "POS"])
