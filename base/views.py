from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum, Prefetch
from django.http import JsonResponse
from django.utils import timezone
from base.models import Category, Table
from .forms import RestaurantCreateForm, OrderForm, OrderItemFormSet , TableForm , OrderItemForm
from .models import SubscriptionPlan, Restaurant, MenuItem, Order, OrderItem , RestaurantCustomization
from django.forms import inlineformset_factory
from django.utils.text import slugify
from .utils import generate_unique_subdomain

def home(request):
    return render(request, 'home/index.html')


# @login_required
# def create_restaurant(request):
#     if request.method == 'POST':
#         form = RestaurantCreateForm(request.POST, request.FILES)
#         if form.is_valid():
#             restaurant = form.save(commit=False)
#             restaurant.owner = request.user
            
#             plan = SubscriptionPlan.objects.filter(
#                 plan_type='starter',
#                 is_active=True
#             ).first()
            
#             if not plan:
#                 form.add_error(None, "Aucun plan actif disponible.")
#                 return render(request, 'admin_user/create_restaurant.html', {'form': form})
            
#             restaurant.subscription_plan = plan
#             restaurant.subscription_start = timezone.now()
#             restaurant.subscription_end = timezone.now() + timedelta(days=plan.duration_days)
#             restaurant.save()
#             return redirect('dashboard')
#     else:
#         form = RestaurantCreateForm()
    
#     return render(request, 'admin_user/create_restaurant.html', {'form': form})


@login_required
def create_restaurant(request):
    if request.method == 'POST':
        form = RestaurantCreateForm(request.POST, request.FILES)
        if form.is_valid():
            restaurant = form.save(commit=False)
            restaurant.slug = slugify(restaurant.name)
            restaurant.subdomain = generate_unique_subdomain(restaurant.name)

            
            
            # Rechercher un plan "Starter" (notez la majuscule dans l'affichage mais minuscule dans la valeur)
            plan = SubscriptionPlan.objects.filter(
                plan_type='starter',  # C'est la valeur dans la base (minuscule)
                is_active=True
            ).first()
            
            # Si aucun plan starter n'est trouvé, créer un par défaut
            if not plan:
                # Créer un plan starter par défaut
                plan, created = SubscriptionPlan.objects.get_or_create(
                    name='Starter Plan',
                    plan_type='starter',
                    defaults={
                        'price': 0.00,
                        'duration_days': 30,
                        'max_menu_items': 50,
                        'max_tables': 10,
                        'custom_domain': False,
                        'analytics': False,
                        'priority_support': False,
                        'remove_branding': False,
                        'is_active': True,
                    }
                )
            
            restaurant.subscription_plan = plan
            restaurant.subscription_start = timezone.now()
            restaurant.subscription_end = timezone.now() + timedelta(days=plan.duration_days)
            restaurant.save()
            return redirect('dashboard')
    else:
        form = RestaurantCreateForm()
    
    return render(request, 'admin_user/create_restaurant.html', {'form': form})


@login_required
def dashboard(request):
    user = request.user
    restaurant = Restaurant.objects.filter(owner=user).first()
    
    if not restaurant:
        return render(request, "admin_user/no_restaurant.html")
    
    today = timezone.now().date()
    last_7_days = today - timedelta(days=6)
    
    total_orders = Order.objects.filter(restaurant=restaurant).count()
    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    ).count()
    
    total_revenue = Order.objects.filter(
        restaurant=restaurant,
        status__in=["confirmed", "preparing", "ready", "delivered"]
    ).aggregate(total=Sum("total"))["total"] or 0
    
    active_menu_items = MenuItem.objects.filter(
        restaurant=restaurant,
        is_available=True
    ).count()
    
    active_tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).count()
    
    orders_by_day = (
        Order.objects.filter(
            restaurant=restaurant,
            created_at__date__gte=last_7_days
        )
        .extra(select={'day': "date(created_at)"})
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    
    days = []
    orders_count = []
    
    for item in orders_by_day:
        day_obj = datetime.strptime(item['day'], "%Y-%m-%d").date()
        days.append(day_obj.strftime("%d/%m"))
        orders_count.append(item['count'])
    
    order_types = (
        Order.objects.filter(restaurant=restaurant)
        .values('order_type')
        .annotate(count=Count('id'))
    )
    
    type_labels = []
    type_values = []
    
    for o in order_types:
        type_labels.append(o['order_type'])
        type_values.append(o['count'])
    
    context = {
        "restaurant": restaurant,
        "total_orders": total_orders,
        "today_orders": today_orders,
        "total_revenue": total_revenue,
        "active_menu_items": active_menu_items,
        "active_tables": active_tables,
        "days": days,
        "orders_count": orders_count,
        "type_labels": type_labels,
        "type_values": type_values,
    }
    
    return render(request, "admin_user/index.html", context)


@login_required
def create_manual_order(request):
    restaurant = request.user.restaurants.first()
    
    if not restaurant:
        messages.error(request, "Aucun restaurant trouvé.")
        return redirect("dashboard")
    
    # Récupération des catégories avec leurs items disponibles
    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=MenuItem.objects.filter(is_available=True, restaurant=restaurant)
        )
    )
    
    if request.method == "POST":
        order_form = OrderForm(request.POST, restaurant=restaurant)
        
        # Créer le formset avec le bon préfixe
        formset = OrderItemFormSet(
            request.POST,
            prefix='items'
        )
        
        if order_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Créer la commande
                    order = order_form.save(commit=False)
                    order.restaurant = restaurant
                    order.save()
                    
                    # Associer le formset à la commande
                    formset.instance = order
                    
                    # Sauvegarder le formset
                    instances = formset.save(commit=False)
                    
                    # Pour chaque OrderItem, définir le prix actuel du menu item
                    for instance in instances:
                        instance.price = instance.menu_item.discount_price or instance.menu_item.price
                        instance.save()
                    
                    # Calculer le total
                    order.calculate_total()
                    order.save()
                
                messages.success(request, f"Commande #{order.id} créée avec succès.")
                return redirect("orders_list")
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la création de la commande: {str(e)}")
        else:
            # Afficher les erreurs de validation
            for field, errors in order_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            for form in formset:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Article: {error}")
    else:
        # GET request - formulaire vide
        order_form = OrderForm(restaurant=restaurant)
        formset = OrderItemFormSet(prefix='items')
    
    return render(request, "admin_user/orders/create_manual_order.html", {
        "order_form": order_form,
        "formset": formset,
        "categories": categories,
        "restaurant": restaurant,
    })
@login_required
def update_order(request, order_id):
    restaurant = request.user.restaurants.first()
    
    if not restaurant:
        messages.error(request, "Aucun restaurant trouvé.")
        return redirect("dashboard")
    
    # Récupérer la commande
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    # Récupération des catégories avec leurs items disponibles
    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=MenuItem.objects.filter(is_available=True, restaurant=restaurant)
        )
    )
    
    # Créer le formset pour les OrderItem
    OrderItemFormSet = inlineformset_factory(
        Order,
        OrderItem,
        form=OrderItemForm,
        extra=0,
        can_delete=True,
        fields=['menu_item', 'quantity']
    )
    
    if request.method == "POST":
        order_form = OrderForm(request.POST, instance=order, restaurant=restaurant)
        formset = OrderItemFormSet(request.POST, instance=order, prefix='items')
        
        if order_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Sauvegarder la commande
                    order = order_form.save()
                    
                    # Sauvegarder les articles existants
                    formset.save()
                    
                    # Traiter les nouveaux articles
                    new_items_count = int(request.POST.get('new-items-TOTAL_FORMS', 0))
                    for i in range(new_items_count):
                        menu_item_id = request.POST.get(f'new-items-{i}-menu_item')
                        quantity = request.POST.get(f'new-items-{i}-quantity')
                        
                        if menu_item_id and quantity:
                            menu_item = MenuItem.objects.get(id=menu_item_id, restaurant=restaurant)
                            OrderItem.objects.create(
                                order=order,
                                menu_item=menu_item,
                                quantity=quantity,
                                price=menu_item.discount_price or menu_item.price
                            )
                    
                    # Recalculer le total
                    order.calculate_total()
                    order.save()
                
                messages.success(request, f"Commande #{order.id} mise à jour avec succès.")
                return redirect("orders_list")
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        # GET request - formulaire pré-rempli
        order_form = OrderForm(instance=order, restaurant=restaurant)
        formset = OrderItemFormSet(instance=order, prefix='items')
    
    # Préparer les données pour le template
    existing_items = []
    for item in order.items.all():
        existing_items.append({
            'id': item.id,
            'menu_item_id': item.menu_item.id,
            'name': item.menu_item.name,
            'price': float(item.price),
            'quantity': item.quantity,
            'image_url': item.menu_item.image.url if item.menu_item.image else '',
            'subtotal': float(item.get_total())
        })
    
    return render(request, "admin_user/orders/update_order.html", {
        "order": order,
        "order_form": order_form,
        "formset": formset,
        "categories": categories,
        "restaurant": restaurant,
        "existing_items": existing_items,
    })
@login_required
def delete_order(request, order_id):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    
    if not restaurant:
        messages.error(request, "Aucun restaurant trouvé.")
        return redirect("dashboard")
    
    try:
        order = Order.objects.get(id=order_id, restaurant=restaurant)
        
        if request.method == "POST":
            order_id = order.id
            order.delete()
            messages.success(request, f"Commande #{order_id} supprimée avec succès.")
            return redirect("orders_list")
        
    except Order.DoesNotExist:
        messages.error(request, "Commande non trouvée.")
    
    return redirect("orders_list")
@login_required
def orders_list(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    orders = Order.objects.filter(restaurant=restaurant).order_by("-created_at")
    
    return render(request, "admin_user/orders/list_orders.html", {
        "restaurant": restaurant,
        "orders": orders
    })

@login_required
@login_required
def order_change_status(request, pk):
    # Correction: "restaurant" au lieu de "restaurent"
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    
    if not restaurant:
        messages.error(request, "Aucun restaurant trouvé.")
        return redirect("orders_list")
    
    order = get_object_or_404(Order, pk=pk, restaurant=restaurant)
    
    # Récupérer le nouveau statut
    new_status = request.POST.get("status")
    
    # Valider que le statut est parmi les choix valides
    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    
    if new_status not in valid_statuses:
        messages.error(request, "Statut invalide.")
        return redirect("orders_list")
    
    # Mettre à jour le statut
    order.status = new_status
    order.save()
    
    # Message de succès
    status_display = dict(Order.STATUS_CHOICES).get(new_status, new_status)
    messages.success(request, f"Statut de la commande #{order.id} mis à jour: {status_display}")
    
    return redirect("orders_list")

@login_required
def order_detail(request, pk):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    order = get_object_or_404(Order, pk=pk, restaurant=restaurant)
    
    return render(request, "admin_user/orders/detail_orders.html", {
        "order": order,
        "restaurant": restaurant
    })


@login_required
def menus_list(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    categories = Category.objects.filter(restaurant=restaurant)
    
    return render(request, "admin_user/menus/list_menu.html", {
        "restaurant": restaurant,
        "categories": categories
    })


@login_required
def menu_create(request):
    print(request)
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    categories = Category.objects.filter(restaurant=restaurant)
    
    if request.method == "POST":
        print("POST =", request.POST)
        print("FILES =", request.FILES)
        MenuItem.objects.create(
            restaurant=restaurant,
            category_id=request.POST.get("category"),
            name=request.POST.get("name"),
            price=request.POST.get("price"),
            description=request.POST.get("description"),
            is_available=True,
            image=request.FILES.get("image"),
        )
        return redirect("menus_list")
    
    return render(request, "admin_user/menus/create_menus.html", {
        "restaurant": restaurant,
        "categories": categories
    })


@login_required
def menu_update(request, pk):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    menu_item = get_object_or_404(MenuItem, pk=pk, restaurant=restaurant)
    
    if request.method == "POST":
        menu_item.name = request.POST.get("name")
        menu_item.price = request.POST.get("price")
        menu_item.description = request.POST.get("description")
        
        category_id = request.POST.get("category")
        if category_id:
            menu_item.category_id = category_id
        
        if request.FILES.get("image"):
            menu_item.image = request.FILES.get("image")
        
        menu_item.save()
        return redirect("menus_list")
    
    categories = Category.objects.filter(restaurant=restaurant)
    
    return render(request, "admin_user/menus/update_menu.html", {
        "restaurant": restaurant,
        "menu_item": menu_item,
        "categories": categories
    })


@login_required
def change_menu_status(request, pk):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    menu_item = get_object_or_404(MenuItem, pk=pk, restaurant=restaurant)
    menu_item.is_available = not menu_item.is_available
    menu_item.save()
    
    return redirect("menus_list")


@login_required
def menu_delete(request, pk):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    menu_item = get_object_or_404(MenuItem, pk=pk, restaurant=restaurant)
    menu_item.delete()
    return redirect("menus_list")


@login_required
def create_category(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        
        if not name:
            return render(request, "admin_user/create_category.html", {
                "restaurant": restaurant,
                "error": "Le nom de la catégorie est obligatoire"
            })
        
        if not description:
            return render(request, "admin_user/create_category.html", {
                "restaurant": restaurant,
                "error": "La description de la catégorie est obligatoire"
            })
        
        if not image:
            return render(request, "admin_user/create_category.html", {
                "restaurant": restaurant,
                "error": "L'image de la catégorie est obligatoire"
            })
        
        if Category.objects.filter(restaurant=restaurant, name=name).exists():
            return render(request, "admin_user/create_category.html", {
                "restaurant": restaurant,
                "error": "La catégorie existe déjà"
            })
        
        Category.objects.create(
            restaurant=restaurant,
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            image=request.FILES.get("image"),
        )
        return redirect("menus_list")
    
    return render(request, "admin_user/menus/create_category.html", {
        "restaurant": restaurant
    })


@login_required
def create_category_modale(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    
    if request.method == "POST":
        name = request.POST.get("name")
        
        if not name:
            return JsonResponse({"error": "Nom requis"}, status=400)
        
        if Category.objects.filter(restaurant=restaurant, name__iexact=name).exists():
            return JsonResponse({"error": "Cette catégorie existe déjà"}, status=400)
        
        category = Category.objects.create(
            restaurant=restaurant,
            name=name
        )
        
        return JsonResponse({
            "id": category.id,
            "name": category.name
        })
    
    return JsonResponse({"error": "Méthode non autorisée"}, status=405)


# @login_required
# def tables_list(request):
#     restaurant = Restaurant.objects.filter(owner=request.user).first()
#     tables = Table.objects.filter(restaurant=restaurant)
    
#     return render(request, "admin_user/list_table.html", {
#         "restaurant": restaurant,
#         "tables": tables
#     })


# @login_required
# def table_create(request):
#     restaurant = Restaurant.objects.filter(owner=request.user).first()
    
#     if request.method == "POST":
#         Table.objects.create(
#             restaurant=restaurant,
#             number=request.POST.get("number"),
#             capacity=request.POST.get("capacity")
#         )
#         return redirect("tables_list")
    
#     return render(request, "admin_user/create_table.html", {
#         "restaurant": restaurant
#     })


# @login_required
# def customization(request):
#     restaurant = Restaurant.objects.filter(owner=request.user).first()
    
#     if request.method == "POST":
#         restaurant.primary_color = request.POST.get("primary_color")
#         restaurant.secondary_color = request.POST.get("secondary_color")
#         restaurant.save()
#         return redirect("customization")
    
#     return render(request, "admin_user/customization.html", {
#         "restaurant": restaurant
#     })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Restaurant, RestaurantCustomization
from django.core.files.storage import FileSystemStorage

@login_required
def customization(request):
    # Récupérer le restaurant de l'utilisateur
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    
    # Récupérer ou créer la personnalisation associée
    customization_obj, created = RestaurantCustomization.objects.get_or_create(
        restaurant=restaurant,
        defaults={
            'primary_color': '#16a34a',
            'secondary_color': '#f97316',
            'font_family': 'poppins'
        }
    )
    
    if request.method == "POST":
        # Gestion des couleurs
        customization_obj.primary_color = request.POST.get("primary_color", customization_obj.primary_color)
        customization_obj.secondary_color = request.POST.get("secondary_color", customization_obj.secondary_color)
        
        # Gestion de la typographie
        font_family = request.POST.get("font_family")
        if font_family in dict(RestaurantCustomization.FONT_CHOICES):
            customization_obj.font_family = font_family
        
        # Gestion du logo
        if 'logo' in request.FILES:
            # Supprimer l'ancien logo si existe
            if customization_obj.logo:
                customization_obj.logo.delete(save=False)
            customization_obj.logo = request.FILES['logo']
        
        # Gestion de l'image de couverture
        if 'cover_image' in request.FILES:
            # Supprimer l'ancienne couverture si existe
            if customization_obj.cover_image:
                customization_obj.cover_image.delete(save=False)
            customization_obj.cover_image = request.FILES['cover_image']
        
        # Option de thème personnalisé
        customization_obj.use_custom_theme = 'use_custom_theme' in request.POST
        
        try:
            customization_obj.save()
            messages.success(request, "Personnalisation enregistrée avec succès !")
            return redirect("customization")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")
    
    # Préparer le contexte
    context = {
        "restaurant": restaurant,
        "customization": customization_obj,
        "font_choices": RestaurantCustomization.FONT_CHOICES,
        "default_colors": {
            'primary': '#16a34a',
            'secondary': '#f97316'
        }
    }
    
    return render(request, "admin_user/customization.html", context)

@login_required
def reset_customization(request):
    """Réinitialiser les personnalisations aux valeurs par défaut"""
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    
    if RestaurantCustomization.objects.filter(restaurant=restaurant).exists():
        customization_obj = restaurant.customization
        customization_obj.primary_color = '#16a34a'
        customization_obj.secondary_color = '#f97316'
        customization_obj.font_family = 'poppins'
        
        # Supprimer les images
        if customization_obj.logo:
            customization_obj.logo.delete(save=False)
            customization_obj.logo = None
        if customization_obj.cover_image:
            customization_obj.cover_image.delete(save=False)
            customization_obj.cover_image = None
        
        customization_obj.save()
        messages.info(request, "Personnalisations réinitialisées aux valeurs par défaut.")
    
    return redirect("customization")

# @login_required
# def restaurant_settings(request):
#     restaurant = Restaurant.objects.filter(owner=request.user).first()
    
#     if request.method == "POST":
#         restaurant.name = request.POST.get("name")
#         restaurant.phone = request.POST.get("phone")
#         restaurant.email = request.POST.get("email")
#         restaurant.address = request.POST.get("address")
#         restaurant.save()
#         return redirect("restaurant_settings")
    
#     return render(request, "admin_user/settings.html", {
#         "restaurant": restaurant
#     })
    

#   #----Table ----#

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Restaurant
from datetime import datetime, timedelta

@login_required
def restaurant_settings(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    
    # Données pour les sélecteurs
    # categories = [
    #     {'value': 'french', 'label': '🇫🇷 Française'},
    #     {'value': 'italian', 'label': '🇮🇹 Italienne'},
    #     {'value': 'asian', 'label': '🥢 Asiatique'},
    #     {'value': 'burger', 'label': '🍔 Burger/Fast-food'},
    #     {'value': 'pizza', 'label': '🍕 Pizza'},
    #     {'value': 'vegan', 'label': '🥗 Végétarien/Végan'},
    #     {'value': 'seafood', 'label': '🐟 Fruits de mer'},
    #     {'value': 'fusion', 'label': '🌍 Fusion'},
    #     {'value': 'other', 'label': '📝 Autre'},
    # ]
    
    # price_ranges = [
    #     {'value': 'cheap', 'label': '€ - Économique'},
    #     {'value': 'medium', 'label': '€€ - Moyenne gamme'},
    #     {'value': 'expensive', 'label': '€€€ - Haut de gamme'},
    #     {'value': 'luxury', 'label': '€€€€ - Luxe'},
    # ]
    
    # services = [
    #     {
    #         'value': 'delivery',
    #         'label': 'Livraison',
    #         'description': 'Livraison à domicile'
    #     },
    #     {
    #         'value': 'takeaway',
    #         'label': 'À emporter',
    #         'description': 'Commandes à emporter'
    #     },
    #     {
    #         'value': 'reservation',
    #         'label': 'Réservation',
    #         'description': 'Réservation en ligne'
    #     },
    #     {
    #         'value': 'terrace',
    #         'label': 'Terrasse',
    #         'description': 'Service en terrasse'
    #     },
    #     {
    #         'value': 'parking',
    #         'label': 'Parking',
    #         'description': 'Parking disponible'
    #     },
    #     {
    #         'value': 'wifi',
    #         'label': 'WiFi',
    #         'description': 'WiFi gratuit'
    #     },
    #     {
    #         'value': 'kids',
    #         'label': 'Enfants',
    #         'description': 'Menu enfants'
    #     },
    #     {
    #         'value': 'disabled',
    #         'label': 'Accessibilité',
    #         'description': 'Accès handicapés'
    #     },
    #     {
    #         'value': 'credit_card',
    #         'label': 'Carte bancaire',
    #         'description': 'Paiement par carte'
    #     },
    # ]
    
    # # Horaires par défaut
    days_of_week = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
    schedules = {}
    
    for day in days_of_week:
        schedules[day] = {
            'ouverture': restaurant.opening_hours.get(f'{day}_open', '09:00'),
            'fermeture': restaurant.opening_hours.get(f'{day}_close', '22:00'),
        }
    
    # Heures disponibles pour les sélecteurs
    hours = []
    for hour in range(0, 24):
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"
            hours.append(time_str)
    
    if request.method == "POST":
        # Informations de base
        restaurant.name = request.POST.get("name", restaurant.name)
        restaurant.description = request.POST.get("description", restaurant.description)
        restaurant.phone = request.POST.get("phone", restaurant.phone)
        restaurant.email = request.POST.get("email", restaurant.email)
        restaurant.address = request.POST.get("address", restaurant.address)
        
        # Catégorie et prix
        # restaurant.category = request.POST.get("category", restaurant.category)
        # restaurant.price_range = request.POST.get("price_range", restaurant.price_range)
        
        # Horaires d'ouverture
        opening_hours = {}
        for day in days_of_week:
            open_key = f"{day}_ouverture"
            close_key = f"{day}_fermeture"
            if open_key in request.POST and close_key in request.POST:
                opening_hours[f"{day}_open"] = request.POST.get(open_key)
                opening_hours[f"{day}_close"] = request.POST.get(close_key)
        
        if opening_hours:
            restaurant.opening_hours = opening_hours
        
        # Services
        # selected_services = request.POST.getlist("services", [])
        # restaurant.services = selected_services
        
        try:
            restaurant.save()
            messages.success(request, "Les paramètres ont été mis à jour avec succès !")
            return redirect("restaurant_settings")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}")
    
    # Récupérer les services du restaurant
    # restaurant_services = restaurant.services or []
    
    context = {
        "restaurant": restaurant,
        # "categories": categories,
        # "price_ranges": price_ranges,
        
       
        "schedules": schedules,
        "hours": hours,
    }
    
    return render(request, "admin_user/settings.html", context)

@login_required
def tables_list(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    
    tables= Table.objects.filter(restaurant=restaurant)
    active_count = tables.filter(is_active=True).count()
    return render(request, "admin_user/tables/table_list.html", {
        'active_count': active_count,
        
        "tables": tables
    })
    
    
@login_required
def table_create(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()

    if not restaurant:
        messages.error(request, "Vous devez d'abord créer un restaurant.")
        return redirect('create_restaurant')

    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            number = form.cleaned_data['number']

            if Table.objects.filter(restaurant=restaurant, number=number).exists():
                messages.error(request, "Cette table existe déjà.")
            else:
                table = form.save(commit=False)
                table.restaurant = restaurant
                table.save()
                messages.success(request, f"Table {table.number} créée avec succès.")
                return redirect('tables_list')
    else:
        form = TableForm()

    return render(
        request,
        'admin_user/tables/table_create.html',
        {
            'restaurant': restaurant,
            'form': form
        }
    )



@login_required
def table_delete(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table.delete()
    messages.success(request, f"Table {table.number} supprimée.")
    return redirect('tables_list')

@login_required
def table_toggle_active(request , table_id):
    table= get_object_or_404(Table, id=table_id)
    table.is_active = not table.is_active
    table.save(update_fields=['is_active'])
    messages.success(request, f"Table {table.number} {'activée' if table.is_active else 'désactivée'}.")
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def table_regenerate_qr(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table.generate_qr_code()
    messages.success(request, f"QR Code de la table {table.number} régénéré.")
    return redirect(request.META.get('HTTP_REFERER'))
@login_required
def table_update(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    if request.method == 'POST':
        form = TableForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            messages.success(request, f"Table {table.number} mise à jour avec succès.")
            return redirect('tables_list')
    else:
        form = TableForm(instance=table)

    return render(
        request,
        'admin_user/tables/table_update.html',
        {
            'table': table,
            'form': form
        }
    )


# ----customisation

@login_required
def customization(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    
    # Récupérer ou créer la personnalisation
    customization_obj, created = RestaurantCustomization.objects.get_or_create(
        restaurant=restaurant
    )
    
    if request.method == "POST":
        customization_obj.primary_color = request.POST.get("primary_color")
        customization_obj.secondary_color = request.POST.get("secondary_color")
        customization_obj.font_family = request.POST.get("font_family", "poppins")
        
        if request.FILES.get("logo"):
            customization_obj.logo = request.FILES.get("logo")
        
        customization_obj.save()
        messages.success(request, "Personnalisation mise à jour avec succès.")
        return redirect("customization")
    
    return render(request, "admin_user/customization.html", {
        "restaurant": restaurant,
        "customization": customization_obj
    })
