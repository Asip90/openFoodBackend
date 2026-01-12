from django.urls import path, include
# from . import views
from django.urls import path
from .views import *
urlpatterns = [
    path("api/customer/", include("customer.api.urls")),

    path("t/<uuid:table_token>/", client_menu, name="client_menu"),

    # Panier (AJAX)
    path("t/<uuid:table_token>/cart/", update_cart, name="update_cart"),

    # Checkout
    path("t/<uuid:table_token>/checkout/", checkout, name="checkout"),

    # Confirmation
    path("order/<int:order_id>/confirmation/", order_confirmation, name="order_confirmation"),
    path('item/<str:item_id>/details/', get_item_details, name='get_item_details'),
    path("api/customer/menu/<uuid:table_token>/", menu_api),

]

# from django.urls import path
# from . import views

# urlpatterns = [
#     path('t/<str:table_token>/', views.client_menu, name='client_menu'),
#     path('update_cart/<str:table_token>/', views.update_cart, name='update_cart'),
#     path('checkout/<str:table_token>/', views.checkout, name='checkout'),
#     path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
#     path('item/<str:item_id>/details/', views.get_item_details, name='get_item_details'),
# ]