# fill_subdomains.py
import os
import django

# config Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OpendFood.settings')  # <-- remplace par ton settings
django.setup()

from django.utils.text import slugify
from base.models import Restaurant

def generate_unique_subdomain(name):
    base = slugify(name)
    subdomain = base
    i = 1

    while Restaurant.objects.filter(subdomain=subdomain).exists():
        subdomain = f"{base}-{i}"
        i += 1

    return subdomain

restaurants = Restaurant.objects.filter(subdomain__isnull=True) | Restaurant.objects.filter(subdomain="")

for r in restaurants:
    r.slug = r.slug or slugify(r.name)
    r.subdomain = generate_unique_subdomain(r.name)
    r.save(update_fields=["slug", "subdomain"])
    print(f"✔ {r.name} → {r.subdomain}")
