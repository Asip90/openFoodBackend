from django.shortcuts import render
from django.db.models import Prefetch
from base.models import Category, MenuItem
from customer.utils import get_client_context

def client_menu(request, table_token):
    restaurant, table, customization, error = get_client_context(request, table_token)
    if error:
        return error

    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=MenuItem.objects.filter(
                restaurant=restaurant,
                is_available=True
            )
        )
    ).order_by("order")

    cart_key = f"cart_{restaurant.id}_{table_token}"
    cart = request.session.get(cart_key, {})

    cart_total = sum(
        float(item["price"]) * item["quantity"]
        for item in cart.values()
    )

    context = {
        "restaurant": restaurant,
        "table": table,
        "customization": customization,
        "categories": categories,
        "cart": cart,
        "cart_total": cart_total,
        "cart_count": len(cart),
        "table_token": table_token,
    }

    return render(request, "customer/menu.html", context)


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from base.models import MenuItem
from .utils import get_client_context

@csrf_exempt
def update_cart(request, table_token):
    if request.method != "POST":
        return JsonResponse({"success": False})

    restaurant, table, _, error = get_client_context(request, table_token)
    if error:
        return JsonResponse({"success": False, "error": "Contexte invalide"})

    data = json.loads(request.body)
    action = data.get("action")
    item_id = str(data.get("item_id"))

    cart_key = f"cart_{restaurant.id}_{table_token}"
    cart = request.session.get(cart_key, {})

    if action == "add":
        item = MenuItem.objects.get(
            id=item_id,
            restaurant=restaurant,
            is_available=True
        )

        if item_id in cart:
            cart[item_id]["quantity"] += 1
        else:
            cart[item_id] = {
                "name": item.name,
                "price": str(item.discount_price or item.price),
                "quantity": 1,
                "image": item.image.url if item.image else None
            }

    elif action == "update":
        qty = int(data.get("quantity", 1))
        if item_id in cart:
            if qty > 0:
                cart[item_id]["quantity"] = qty
            else:
                del cart[item_id]

    elif action == "remove":
        cart.pop(item_id, None)

    request.session[cart_key] = cart
    request.session.modified = True

    total = sum(
        float(i["price"]) * i["quantity"]
        for i in cart.values()
    )

    return JsonResponse({
        "success": True,
        "total": total,
        "count": len(cart)
    })

# checkout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from base.models import Order, OrderItem
from customer.utils import get_client_context

def checkout(request, table_token):
    restaurant, table, customization, error = get_client_context(request, table_token)
    if error:
        return error

    cart_key = f"cart_{restaurant.id}_{table_token}"
    cart = request.session.get(cart_key, {})

    if not cart:
        messages.error(request, "Votre panier est vide")
        return redirect("client_menu", table_token=table_token)

    if request.method == "POST":
        with transaction.atomic():
            order = Order.objects.create(
                restaurant=restaurant,
                table=table,
                order_type="dine_in",
                status="pending"
            )

            for item_id, data in cart.items():
                OrderItem.objects.create(
                    order=order,
                    menu_item_id=item_id,
                    quantity=data["quantity"],
                    price=data["price"]
                )

            order.calculate_total()
            del request.session[cart_key]

            return redirect("order_confirmation", order_id=order.id)

    return render(request, "customer/checkout.html", {
        "restaurant": restaurant,
        "customization": customization,
        "table": table,
        "cart": cart,
    })


# confirmation 
from django.shortcuts import render, get_object_or_404
from base.models import Order, RestaurantCustomization

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    customization = RestaurantCustomization.objects.filter(
        restaurant=order.restaurant
    ).first()

    return render(request, "customer/confirmation.html", {
        "order": order,
        "restaurant": order.restaurant,
        "customization": customization
    })
