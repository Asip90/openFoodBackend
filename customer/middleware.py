from django.utils.deprecation import MiddlewareMixin
from base.models import Restaurant

class SubdomainMiddleware(MiddlewareMixin):

    def process_request(self, request):
        host = request.get_host().split(':')[0]  
        # ex: le-luxury-house.127.0.0.1

        parts = host.split('.')

        request.subdomain = None
        request.restaurant = None

        # --------------------------
        # LOCALHOST / 127.0.0.1
        # --------------------------
        if host.endswith("localhost"):
            # ex: resto.localhost
            if len(parts) > 1:
                request.subdomain = parts[0]

        elif host.endswith("127.0.0.1"):
            # ex: resto.127.0.0.1
            if len(parts) > 4:
                request.subdomain = parts[0]

        # --------------------------
        # PRODUCTION
        # --------------------------
        else:
            # ex: resto.mondomaine.com
            if len(parts) > 2:
                request.subdomain = parts[0]

        # --------------------------
        # Charger le restaurant
        # --------------------------
        if request.subdomain:
            request.restaurant = Restaurant.objects.filter(
                subdomain=request.subdomain,
                is_active=True
            ).first()
