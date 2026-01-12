from rest_framework import serializers
from base.models import Category, MenuItem, Order, OrderItem, RestaurantCustomization
from django.conf import settings
from rest_framework import serializers
from base.models import MenuItem


from django.conf import settings
from rest_framework import serializers
from base.models import MenuItem

class MenuItemSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "name",
            "description",
            "price",
            "discount_price",
            "image",
            "ingredients",
            "allergens",
            "is_vegetarian",
            "is_vegan",
            "is_spicy",
            "preparation_time",
        ]

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return f"{settings.BACKEND_DOMAIN}{obj.image.url}"
class CategorySerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True)

    class Meta:
        model = Category
        fields = ["id", "name", "items"]


from django.conf import settings
from rest_framework import serializers
from base.models import RestaurantCustomization

class RestaurantCustomizationSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantCustomization
        fields = [
            "primary_color",
            "secondary_color",
            "font_family",
            "logo",
            "cover_image"
        ]

    def get_logo(self, obj):
        if not obj.logo:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.logo.url)
        return f"{settings.BACKEND_DOMAIN}{obj.logo.url}"

    def get_cover_image(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.cover_image.url)
        return f"{settings.BASE_URL}{obj.cover_image.url}"



class OrderItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="menu_item.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["name", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "order_type",
            "subtotal",
            "tax",
            "total",
            "items",
            "created_at",
        ]

# serializers.py
from rest_framework import serializers
from base.models import Order, OrderItem, MenuItem, Table

class OrderItemCreateSerializer(serializers.Serializer):
    menu_item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class CreateOrderSerializer(serializers.Serializer):
    table_id = serializers.IntegerField(required=False)
    order_type = serializers.ChoiceField(choices=Order.ORDER_TYPE_CHOICES, default='dine_in')
    notes = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("La commande doit contenir au moins un item.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        tableToken = validated_data.pop('tableToken', None)
        table = None
        if tableToken:
            table = Table.objects.get(pk=tableToken)
        #recuperer le restaurant
        restaurant = table.restaurant
        print(restaurant)
        # Création de la commande
        order = Order.objects.create(
            table=table,
            order_type=validated_data.get('order_type', 'dine_in'),
            notes=validated_data.get('notes', '')
        )

        # Création des OrderItems
        for item_data in items_data:
            menu_item = MenuItem.objects.get(pk=item_data['menu_item'])
            price = menu_item.discount_price or menu_item.price
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                price=price
            )

        # Calcul totals côté backend
        order.calculate_total()
        return order
