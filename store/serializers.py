from django.conf import settings
from rest_framework import serializers
from .models import *
from .geo import courier_pos

class ReviewS(serializers.ModelSerializer):
    class Meta: model = Review; exclude = ["product", "user"]

class ProductS(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    rating = serializers.FloatField()
    reviews = ReviewS(many=True, read_only=True)
    class Meta: model = Product; fields = "__all__"
    def get_image_url(self, o):
        if o.image: return self.context["request"].build_absolute_uri(o.image.url)
        return o.image_path

class ItemS(serializers.ModelSerializer):
    class Meta: model = OrderItem; fields = ["product", "name", "size", "color", "quantity", "price"]

class OrderS(serializers.ModelSerializer):
    items = ItemS(many=True, read_only=True)
    store = serializers.SerializerMethodField(); courier = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    payment_label = serializers.CharField(source="get_payment_display", read_only=True)
    payment_status_label = serializers.CharField(source="get_payment_status_display", read_only=True)
    class Meta:
        model = Order; fields = "__all__"
        read_only_fields = ["user", "number", "total", "status", "created", "dispatched_at", "dest_lat", "dest_lng", "current_lat", "current_lng", "subtotal", "discount", "gift", "payment_status", "expected_delivery", "dispatched_at", "out_for_delivery_at", "delivered_at"]
    def get_store(self, o): return settings.STORE
    def get_courier(self, o): return courier_pos(o)
