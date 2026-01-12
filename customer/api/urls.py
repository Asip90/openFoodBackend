from django.urls import path
from .views import *

urlpatterns = [
    path("menu/<uuid:table_token>/", client_menu_api),
    path("create-order/<uuid:table_token>/", create_order)
    # path("cart/<uuid:table_token>/", cart_api),
    # path("checkout/<uuid:table_token>/", checkout_api),
]
