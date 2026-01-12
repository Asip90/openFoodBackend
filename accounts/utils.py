from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse

from .models import User


def send_verification_email(request, user):
    token = user.email_token

    verification_url = request.build_absolute_uri(
        reverse("verify-email", args=[str(token)])
    )

    subject = "Vérification de votre email"
    message = f"""
Bonjour {user.first_name},

Merci pour votre inscription.

Cliquez sur le lien ci-dessous pour vérifier votre adresse email :
{verification_url}

Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
