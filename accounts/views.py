from django.shortcuts import get_object_or_404, render
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login , logout
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from base.views import dashboard
from .utils import send_verification_email
from .models import User


def connexion(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is None:
            messages.error(request, "Email ou mot de passe incorrect.")
            return redirect("connexion")

        if not user.email_verified:
            messages.error(
                request,
                "Votre email n'est pas encore vérifié. Vérifiez votre boîte mail."
            )
            return redirect("connexion")

        login(request, user)
        return redirect(dashboard)  # adapte ici

    return render(request, "auth/connexion.html")

   
   
def inscription(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email existe déjà.")
            return redirect("inscription")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )

        send_verification_email(request, user)

        messages.success(
            request,
            "Compte créé avec succès. Vérifiez votre email pour activer votre compte."
        )
        return redirect("connexion")

    return render(request, "auth/inscription.html")


def verify_email(request, token):
    user = get_object_or_404(User, email_token=token)

    if user.email_verified:
        messages.info(request, "Votre email est déjà vérifié.")
        return redirect("connexion")

    user.email_verified = True
    user.email_token = None  # optionnel mais recommandé
    user.save()

    messages.success(request, "Email vérifié avec succès 🎉")
    return redirect("connexion")

# @login_required
def log_out(request):
    logout(request)
    return redirect("connexion")
    