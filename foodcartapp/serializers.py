from rest_framework import serializers
from django.db import transaction
from phonenumber_field.serializerfields import PhoneNumberField

from .models import Product, Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']


class OrderCreateSerializer(serializers.ModelSerializer):
    phonenumber = PhoneNumberField()
    products = OrderItemSerializer(many=True, allow_empty=False, write_only=True)

    class Meta:
        model = Order
        fields = ['firstname', 'lastname', 'phonenumber', 'address', 'products']

    def create(self, validated_order):
        products = validated_order.pop('products')
        with transaction.atomic():
            order = Order.objects.create(**validated_order)
            for product_item in products:
                OrderItem.objects.create(order=order, **product_item)
        return order


class OrderReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'phonenumber', 'address', 'created_at']
