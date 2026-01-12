from django.db import models
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.contrib.auth.models import Group, Permission
import uuid
import hashlib
import random


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    email_verified = models.BooleanField(default=False)
    email_token = models.UUIDField(
        default=uuid.uuid4,
        null=True,
        blank=True,
        editable=False
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    transfer_pin_hash = models.CharField(max_length=64, blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    def set_transfer_pin(self, pin: str):
        self.transfer_pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        self.save()

    def check_transfer_pin(self, pin: str) -> bool:
        return self.transfer_pin_hash == hashlib.sha256(pin.encode()).hexdigest()

    
    


    objects = UserManager()
    groups = models.ManyToManyField(
        Group,
        related_name="accounts_users",
        blank=True
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="accounts_user_permissions",
        blank=True
    )


    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]
    
    

