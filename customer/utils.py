
from django.shortcuts import render
from base.models import Restaurant, Table, RestaurantCustomization

def get_client_context(request, table_token):
    # Restaurant injecté par le middleware
    print('depart')
    restaurant = getattr(request, "restaurant", None)
    
    print(restaurant)
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

