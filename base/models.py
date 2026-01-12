# models.py
# from tkinter import N
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import qrcode
from io import BytesIO
from django.core.files import File
from decimal import Decimal


from accounts.models import User

import uuid



class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    
    # Features
    max_menu_items = models.IntegerField()
    max_tables = models.IntegerField()
    custom_domain = models.BooleanField(default=False)
    analytics = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    remove_branding = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.price}€"



class Restaurant(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurants')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    # subdomain = models.CharField(max_length=100, unique=True, blank=True)
    subdomain = models.SlugField(unique=True,null=True, blank=True)
    
    # Info restaurant
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    
    # Images
    logo = models.ImageField(upload_to='restaurants/logos/', blank=True)
    cover_image = models.ImageField(upload_to='restaurants/covers/', blank=True)
    
    # Horaires
    opening_hours = models.JSONField(default=dict, blank=True)
    
    # Subscription
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # QR Code
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True)
    
    # Customization
    primary_color = models.CharField(max_length=7, default='#FF6B6B')
    secondary_color = models.CharField(max_length=7, default='#4ECDC4')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 1
            while Restaurant.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug

        if not self.subdomain:
            self.subdomain = self.slug
        super().save(*args, **kwargs)
        
        # Générer QR Code
        if not self.qr_code:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        url = f"https://{self.subdomain}.votredomaine.com"
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color=self.primary_color, back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_{self.slug}.png'
        self.qr_code.save(filename, File(buffer), save=False)
        super().save(update_fields=['qr_code'])
    
    def __str__(self):
        return self.name


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    
    # Prix
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Images
    image = models.ImageField(upload_to='menu_items/', blank=True)
    
    # Info
    ingredients = models.TextField(blank=True)
    allergens = models.CharField(max_length=300, blank=True)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    
    # Stock
    is_available = models.BooleanField(default=True)
    preparation_time = models.IntegerField(help_text="Temps en minutes", default=15)
    
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.price}€"


from django.conf import settings



class Table(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="tables"
    )
    number = models.CharField(max_length=20)
    capacity = models.IntegerField()
    qr_code = models.ImageField(
        upload_to="table_qrcodes/",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    class Meta:
        unique_together = ("restaurant", "number")

    def generate_qr_code(self):
        # Si déjà généré, ne rien faire
        # if self.qr_code:
        #     return

        subdomain = self.restaurant.subdomain or slugify(self.restaurant.name)
        url = f"https://{subdomain}.{settings.FRONTEND_BASE_URL}/t/{self.token}"

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"table_{self.restaurant.slug}_{self.number}.png"
        self.qr_code.save(filename, File(buffer), save=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # Générer QR Code avant le save si la table est nouvelle
        if is_new and not self.qr_code:
            self.generate_qr_code()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Table {self.number} - {self.restaurant.name}"



class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('preparing', 'En préparation'),
        ('ready', 'Prête'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
    ]
    
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Sur place'),
        ('takeaway', 'À emporter'),
        ('delivery', 'Livraison'),
    ]
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Client info
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    
    # Order details
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='dine_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Prix
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        self.subtotal = sum(
            (item.get_total() for item in self.items.all()),
            Decimal("0.00")
        )
        self.tax = self.subtotal * Decimal("0.10")
        self.total = self.subtotal + self.tax
        self.save(update_fields=["subtotal", "tax", "total"])

        
    def __str__(self):
        return f"{self.order_number} - {self.restaurant.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    
    def get_total(self):
        return self.price * self.quantity
    
    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.menu_item.discount_price or self.menu_item.price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"

class Payment(models.Model):
    PAYMENT_METHOD = [
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('mobile', 'Paiement mobile'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment {self.order.order_number} - {self.amount}FCFA"
    
    
class RestaurantCustomization(models.Model):
    FONT_CHOICES = [
        ('inter', 'Inter'),
        ('poppins', 'Poppins'),
        ('montserrat', 'Montserrat'),
        ('roboto', 'Roboto'),
    ]

    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="customization"
    )

    # 🎨 Couleurs
    primary_color = models.CharField(
        max_length=7,
        default="#16a34a",
        help_text="Couleur principale (ex: #16a34a)"
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#f97316",
        help_text="Couleur secondaire"
    )

    # 🖼️ Branding
    logo = models.ImageField(
        upload_to="restaurants/customization/logos/",
        blank=True,
        null=True
    )
    cover_image = models.ImageField(
        upload_to="restaurants/customization/covers/",
        blank=True,
        null=True
    )

    # 🔤 Typographie
    font_family = models.CharField(
        max_length=50,
        choices=FONT_CHOICES,
        default="poppins"
    )

    # 🔄 Options futures
    use_custom_theme = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customisation - {self.restaurant.name}"
