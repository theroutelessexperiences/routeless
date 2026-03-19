from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Experience, Location

class ExperienceSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Experience.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # Fallback to reversing the url if the experience model doesn't have a get_absolute_url
        if hasattr(obj, 'get_absolute_url'):
             return obj.get_absolute_url()
        return reverse('listing_detail', args=[obj.slug])

class LocationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Location.objects.all()

    def location(self, obj):
        # Locations list filtered by the location slug
        return reverse('listing_list') + f"?location={obj.slug}"

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ['home', 'listing_list', 'locations', 'categories']

    def location(self, item):
        return reverse(item)
