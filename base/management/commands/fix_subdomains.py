from django.core.management.base import BaseCommand
from django.utils.text import slugify
from base.models import Restaurant
from base.utils import generate_unique_subdomain

class Command(BaseCommand):
    help = "Génère les sous-domaines pour les restaurants existants"

    def handle(self, *args, **kwargs):
        for restaurant in Restaurant.objects.filter(subdomain__isnull=True):
            base_slug = slugify(restaurant.name)
            slug = base_slug
            i = 1

            while Restaurant.objects.filter(subdomain=slug).exists():
                slug = f"{base_slug}-{i}"
                i += 1

            restaurant.subdomain = generate_unique_subdomain(restaurant.name)
            restaurant.slug = slug
            restaurant.save()

            self.stdout.write(self.style.SUCCESS(
                f"✔ {restaurant.name} → {slug}"
            ))
        print('tache terminer ')
