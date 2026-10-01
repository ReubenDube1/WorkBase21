from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from accounts.models import CareerPath
from .models import Job, TrendingTopic


class JobSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Job.objects.filter(is_active=True).select_related('company')

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return obj.get_absolute_url()


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return TrendingTopic.objects.filter(is_active=True).exclude(body='')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        # (url name, priority) — home and the main listing pages matter
        # most for search, static/legal pages matter least.
        return [
            ('welcome', 1.0),
            ('jobs', 0.9),
            ('jobs_public', 0.8),
            ('jobs_private', 0.8),
            ('internships', 0.9),
            ('learnerships', 0.9),
            ('bursaries', 0.9),
            ('trending_list', 0.8),
            ('careers', 0.8),
            ('market_insights', 0.7),
            ('about', 0.5),
            ('contact', 0.5),
            ('privacy', 0.3),
            ('terms', 0.3),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]


class CareerSitemap(Sitemap):
    """The public Career Explorer pages."""
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return CareerPath.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()

