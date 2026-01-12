from django.urls import path
from accounts.views import *


urlpatterns = [
    
    path('connexion/',connexion,name="connexion"),
    path('inscription/',inscription,name="inscription"),
    path("verify-email/<uuid:token>/", verify_email, name="verify-email"),
    path("logout/", log_out, name="deconnexion"),

]
