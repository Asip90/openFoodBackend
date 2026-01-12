from rest_framework.decorators import api_view
from rest_framework.response import Response
from base.models import Category, MenuItem
from customer.utils import get_client_context
from .serializers import (
    CategorySerializer,
    MenuItemSerializer,
    RestaurantCustomizationSerializer
)

@api_view(["GET"])
def client_menu_api(request, table_token):
    restaurant, table, customization, error = get_client_context(request, table_token)
    if error:
        print('error ic---')
        return Response({"error": "Restaurant ou table invalide"}, status=400)

    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).prefetch_related("items")
    print( restaurant.name , restaurant.subdomain)
    menuItems = MenuItem.objects.filter(
        restaurant=restaurant ,
        is_available = True
    )
    return Response({
        "restaurant": {
            "name": restaurant.name,
            'description': restaurant.description,
            "address":restaurant.address,
            "phone":restaurant.phone,
            "subdomain": restaurant.subdomain,
            "opening_hours": restaurant.opening_hours,
        },
        "table": {
            "id": table.id,
            "number": table.number,
            "token": str(table.token),
        },
        "customization": RestaurantCustomizationSerializer(customization).data,
        "categories": CategorySerializer(categories, many=True).data,
        "menuItems": MenuItemSerializer(menuItems , many =True).data
    })
    



# @api_view(["POST"])
# def cart_api(request, table_token):
#     restaurant, table, _, error = get_client_context(request, table_token)
#     if error:
#         return Response({"error": "Contexte invalide"}, status=400)

#     action = request.data.get("action")
#     item_id = str(request.data.get("item_id"))

#     cart_key = f"cart_{restaurant.id}_{table_token}"
#     cart = request.session.get(cart_key, {})

#     from base.models import MenuItem

#     if action == "add":
#         item = MenuItem.objects.get(id=item_id, restaurant=restaurant)
#         cart.setdefault(item_id, {
#             "name": item.name,
#             "price": str(item.discount_price or item.price),
#             "quantity": 0,
#             "image": item.image.url if item.image else None
#         })
#         cart[item_id]["quantity"] += 1

#     elif action == "update":
#         qty = int(request.data.get("quantity", 1))
#         if qty > 0:
#             cart[item_id]["quantity"] = qty
#         else:
#             cart.pop(item_id, None)

#     elif action == "remove":
#         cart.pop(item_id, None)

#     request.session[cart_key] = cart
#     request.session.modified = True

#     total = sum(
#         float(i["price"]) * i["quantity"]
#         for i in cart.values()
#     )

#     return Response({
#         "cart": cart,
#         "total": total,
#         "count": len(cart)
#     })

# @api_view(["POST"])
# def checkout_api(request, table_token):
#     restaurant, table, _, error = get_client_context(request, table_token)
#     if error:
#         return Response({"error": "Contexte invalide"}, status=400)

#     cart_key = f"cart_{restaurant.id}_{table_token}"
#     cart = request.session.get(cart_key, {})

#     if not cart:
#         return Response({"error": "Panier vide"}, status=400)

#     from base.models import Order, OrderItem
#     from django.db import transaction

#     with transaction.atomic():
#         order = Order.objects.create(
#             restaurant=restaurant,
#             table=table,
#             order_type="dine_in",
#             status="pending"
#         )

#         for item_id, data in cart.items():
#             OrderItem.objects.create(
#                 order=order,
#                 menu_item_id=item_id,
#                 quantity=data["quantity"],
#                 price=data["price"]
#             )

#         order.calculate_total()
#         del request.session[cart_key]

#     return Response({
#         "order_id": order.id,
#         "order_number": order.order_number,
#         "total": order.total
#     })

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from decimal import Decimal
from base.models import Restaurant, Table, Order, OrderItem, MenuItem
from .serializers import OrderSerializer

@api_view(["POST"])
def create_order(request , table_token):
    data = request.data
    print(data)

    # 1️⃣ Récupérer le restaurant
    table = Table.objects.get(token=table_token)
    print(table)
    restaurant =  table.restaurant
    print(restaurant)
   
    order_type = data.get("order_type", "dine_in")
   
    items_data = data.get("items", [])
    if not items_data:
        return Response({"error": "Aucun item fourni."}, status=status.HTTP_400_BAD_REQUEST)

    # 3️⃣ Créer la commande dans une transaction
    try:
        with transaction.atomic():
            order = Order.objects.create(
                restaurant=restaurant,
                table=table,
                order_type=order_type,
                customer_name=data.get("customer_name", ""),
                customer_phone=data.get("customer_phone", ""),
                notes=data.get("notes", "")
            )

            subtotal = Decimal("0.00")

            # 4️⃣ Créer les OrderItem
            for item in items_data:
                try:
                    menu_item = MenuItem.objects.get(id=item["menu_item_id"], restaurant=restaurant, is_available=True)
                except MenuItem.DoesNotExist:
                    raise ValueError(f"Item {item['menu_item_id']} introuvable ou indisponible.")

                quantity = max(int(item.get("quantity", 1)), 1)
                price = menu_item.discount_price or menu_item.price

                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    price=price
                )

                subtotal += price * quantity

            # 5️⃣ Calculer total et taxes
            tax = subtotal * Decimal("0.10")  # exemple 10% TVA
            total = subtotal + tax

            order.subtotal = subtotal
            order.tax = tax
            order.total = total
            order.save()

            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    except ValueError as ve:
        return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": "Erreur lors de la création de la commande."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
