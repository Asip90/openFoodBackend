# from base.models import Wallet
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
import json

from .models import MenuItem , OrderItem


# def get_or_create_wallet(user):
#     wallet, created = Wallet.objects.get_or_create(user=user)
#     return wallet

from django.utils.text import slugify
from base.models import Restaurant

def generate_unique_subdomain(name):
    base = slugify(name)
    subdomain = base
    i = 1

    while Restaurant.objects.filter(subdomain=subdomain).exists():
        subdomain = f"{base}-{i}"
        i += 1

    return subdomain

from django.shortcuts import render
from base.models import Restaurant, Table, RestaurantCustomization

def get_client_context(request, table_token):
    # Restaurant injecté par le middleware
    restaurant = getattr(request, "restaurant", None)

    if not restaurant:
        return None, None, None, render(
            request,
            "customer/error.html",
            {"message": "Restaurant non disponible"}
        )

    try:
        table = Table.objects.get(
            token=table_token,
            restaurant=restaurant,
            is_active=True
        )
    except Table.DoesNotExist:
        return restaurant, None, None, render(
            request,
            "customer/error.html",
            {"message": "Table non valide"}
        )

    customization, _ = RestaurantCustomization.objects.get_or_create(
        restaurant=restaurant,
        defaults={
            "primary_color": "#111827",
            "secondary_color": "#C8A951",
            "font_family": "inter"
        }
    )

    return restaurant, table, customization, None

