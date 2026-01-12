from django.contrib import admin
from django.utils.html import format_html

from .models import (
    SubscriptionPlan,
    Restaurant,
    Category,
    MenuItem,
    Table,
    Order,
    OrderItem,
    Payment
)

# =========================
# SUBSCRIPTION PLAN
# =========================
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'plan_type', 'price', 'duration_days',
        'max_menu_items', 'max_tables',
        'custom_domain', 'analytics',
        'is_active', 'created_at'
    )
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name',)
    ordering = ('price',)


# =========================
# RESTAURANT
# =========================
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'owner', 'subdomain',
        'subscription_plan', 'is_active',
        'qr_preview', 'created_at'
    )
    list_filter = ('is_active', 'subscription_plan')
    search_fields = ('name', 'subdomain', 'owner__email')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('qr_preview', 'created_at', 'updated_at')
    fieldsets = (
        ("Informations générales", {
            'fields': (
                'owner', 'name', 'slug', 'subdomain',
                'description', 'address', 'phone', 'email'
            )
        }),
        ("Images", {
            'fields': ('logo', 'cover_image')
        }),
        ("Horaires", {
            'fields': ('opening_hours',)
        }),
        ("Abonnement", {
            'fields': (
                'subscription_plan',
                'subscription_start',
                'subscription_end',
                'is_active'
            )
        }),
        ("Personnalisation", {
            'fields': ('primary_color', 'secondary_color')
        }),
        ("QR Code", {
            'fields': ('qr_code', 'qr_preview')
        }),
        ("Dates", {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="80" height="80" />',
                obj.qr_code.url
            )
        return "-"
    qr_preview.short_description = "QR Code"


# =========================
# CATEGORY
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'order', 'is_active')
    list_filter = ('restaurant', 'is_active')
    search_fields = ('name',)
    ordering = ('order',)
    prepopulated_fields = {'slug': ('name',)}


# =========================
# MENU ITEM
# =========================
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'restaurant', 'category',
        'price', 'discount_price',
        'is_available', 'is_vegetarian', 'is_spicy'
    )
    list_filter = (
        'restaurant', 'category',
        'is_available', 'is_vegetarian',
        'is_vegan', 'is_spicy'
    )
    search_fields = ('name', 'description', 'ingredients')
    ordering = ('order',)
    prepopulated_fields = {'slug': ('name',)}


# =========================
# TABLE
# =========================
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'restaurant',
        'capacity', 'is_active',
        'qr_preview'
    )
    list_filter = ('restaurant', 'is_active')
    search_fields = ('number',)
    readonly_fields = ('qr_preview',)

    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="80" height="80" />',
                obj.qr_code.url
            )
        return "-"
    qr_preview.short_description = "QR Table"


# =========================
# ORDER ITEMS INLINE
# =========================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'price', 'quantity', 'notes')


# =========================
# ORDER
# =========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'restaurant',
        'order_type', 'status',
        'total', 'created_at'
    )
    list_filter = ('restaurant', 'status', 'order_type')
    search_fields = ('order_number', 'customer_name', 'customer_phone')
    readonly_fields = (
        'order_number', 'subtotal',
        'tax', 'total',
        'created_at', 'updated_at'
    )
    inlines = [OrderItemInline]
    ordering = ('-created_at',)


# =========================
# PAYMENT
# =========================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'amount',
        'payment_method',
        'status', 'created_at'
    )
    list_filter = ('payment_method', 'status')
    search_fields = ('order__order_number', 'transaction_id')
    readonly_fields = ('created_at',)
