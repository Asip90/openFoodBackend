from django import views
from django.urls import path
from base.views import *


urlpatterns = [
    path('',home,name="home"),
    
    path("restaurant/create/", create_restaurant, name="create_restaurant"),
     # Dashboard
    path("dashboard/", dashboard, name="dashboard"),

    # Commandes
    path("orders/", orders_list, name="orders_list"),
    path("orders/create-manual-order/", create_manual_order, name="create_manual_order"),
    path("orders/<int:pk>/", order_detail, name="order_detail"),
    path('orders/<int:order_id>/update/', update_order, name='update_order'),
    path('orders/<int:order_id>/delete/', delete_order, name='delete_order'),
    path("orders/<int:pk>/change-status/", order_change_status, name="order_change_status"),


    # Catégories
    # path("categories/", categories_list, name="categories_list"),
    path("categories/create/", create_category, name="create_category"),
    path("categories/create/modale/", create_category_modale, name="create_category_modale"),

    # Menus
    path("menus/", menus_list, name="menus_list"),
    path("menus/<int:pk>/update/", menu_update, name="menu_update"),
    path("menus/<int:pk>/delete/", menu_delete, name="menu_delete"),
    path("menus/create/", menu_create, name="menu_create"),
    path("menus/<int:pk>/change-availability/", change_menu_status, name="menu_toggle_availability"),
    # Tables
    path("tables/", tables_list, name="tables_list"),
    path("tables/create/", table_create, name="table_create"),
    path("tables/<int:table_id>/delete/", table_delete, name="table_delete"),
    path("tables/<int:table_id>/toggle_active/", table_toggle_active, name="table_toggle_active"),
    path("tables/<int:table_id>/regenerate_qr/", table_regenerate_qr, name="table_regenerate_qr"),
    path("tables/<int:table_id>/update/", table_update, name="table_update"),

    # Personnalisation
    path("customization/", customization, name="customization"),
    path("customization/reset/", reset_customization, name="reset_customization"),

    # Paramètres restaurant
    path("settings/", restaurant_settings, name="restaurant_settings"),
]
