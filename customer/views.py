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
    
    # Calculer les totaux
    cart_items = []
    cart_total = 0
    cart_count = 0
    
    for item_id, item_data in cart.items():
        try:
            menu_item = MenuItem.objects.get(id=item_id, restaurant=restaurant)
            item_total = float(item_data["price"]) * item_data["quantity"]
            cart_total += item_total
            cart_count += item_data["quantity"]
            
            cart_items.append({
                "id": item_id,
                "name": item_data["name"],
                "price": float(item_data["price"]),
                "quantity": item_data["quantity"],
                "image": item_data.get("image"),
                "total": item_total
            })
        except MenuItem.DoesNotExist:
            continue
    
    context = {
        "restaurant": restaurant,
        "table": table,
        "customization": customization,
        "categories": categories,
        "cart": cart_items,  # Liste d'items au lieu de dict
        "cart_total": cart_total,
        "cart_count": cart_count,
        "table_token": table_token,
        "cart_json": json.dumps(cart_items)  # JSON pour JavaScript
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
from django.http import JsonResponse
from base.models import MenuItem

@csrf_exempt
def get_item_details(request, item_id):
    """Retourne les détails d'un article en JSON pour le modal"""
    if request.method != 'GET':
        return JsonResponse({'success': False})
    
    try:
        item = MenuItem.objects.get(id=item_id, is_available=True)
        
        data = {
            'success': True,
            'item': {
                'id': str(item.id),
                'name': item.name,
                'description': item.description,
                'price': str(item.price),
                'discount_price': str(item.discount_price) if item.discount_price else None,
                'image_url': item.image.url if item.image else None,
                'ingredients': item.ingredients,
                'allergens': item.allergens,
                'is_vegetarian': item.is_vegetarian,
                'is_vegan': item.is_vegan,
                'is_spicy': item.is_spicy,
                'preparation_time': item.preparation_time,
                'category': item.category.name if item.category else '',
            }
        }
        
        return JsonResponse(data)
        
    except MenuItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Article non trouvé'})
    
    
    from django.http import JsonResponse
from django.views.decorators.http import require_GET
from customer.utils import get_client_context
from base.models import Category, MenuItem

@require_GET
def menu_api(request, table_token):
    restaurant, table, customization, error = get_client_context(request, table_token)
    if error:
        return JsonResponse({"error": "Restaurant non disponible"}, status=404)

    categories_data = []

    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).prefetch_related("items")

    for category in categories:
        items = category.items.filter(is_available=True)

        categories_data.append({
            "id": category.id,
            "name": category.name,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": str(item.discount_price or item.price),
                    "image": item.image.url if item.image else None,
                }
                for item in items
            ]
        })

    return JsonResponse({
        "restaurant": {
            "id": restaurant.id,
            "name": restaurant.name,
            "logo": restaurant.logo.url if restaurant.logo else None,
        },
        "customization": {
            "primary_color": customization.primary_color,
            "secondary_color": customization.secondary_color,
        },
        "categories": categories_data
    })
