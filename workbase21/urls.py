"""
URL configuration for WorkBase21 project.
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve as static_serve
from django.contrib.sitemaps.views import sitemap

from jobs.views import ads_txt, robots_txt
from jobs.sitemaps import JobSitemap, ArticleSitemap, StaticViewSitemap
from jobs.editor import upload_image as editor_upload_image
from jobs.admin_views import (
    analytics_dashboard, listing_insights, backups_page, backup_download_db,
    backup_download_full, backup_email_now, backup_restore,
)

sitemaps = {
    'jobs': JobSitemap,
    'articles': ArticleSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    # Must come before the admin.site.urls include below so this exact
    # path is matched first — the admin site link (see
    # templates/admin/index.html) points here.
    path('admin/analytics/', analytics_dashboard, name='admin_analytics'),
    path('admin/listing-insights/', listing_insights, name='admin_listing_insights'),
    path('admin/editor/upload-image/', editor_upload_image, name='admin_editor_upload_image'),
    path('admin/backups/', backups_page, name='admin_backups'),
    path('admin/backups/download-database/', backup_download_db, name='admin_backup_download_db'),
    path('admin/backups/download-everything/', backup_download_full, name='admin_backup_download_full'),
    path('admin/backups/email-now/', backup_email_now, name='admin_backup_email_now'),
    path('admin/backups/restore/', backup_restore, name='admin_backup_restore'),
    path('admin/', admin.site.urls),
    path('ads.txt', ads_txt, name='ads_txt'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('accounts/', include('accounts.urls')),
    path('', include('jobs.urls')),
]

# Serve media files (job images, company logos, article images, Z83
# forms). This project doesn't use a separate cloud storage service
# (like S3 or Cloudinary), so Django needs to serve these itself.
#
# IMPORTANT: Django's usual `static()` helper only works when
# DEBUG=True — it silently no-ops otherwise, which is what caused
# uploaded images to 404 in production even though they were saving
# to disk correctly. We wire django.views.static.serve directly here
# instead, so it works regardless of DEBUG.
#
# For a small-to-medium site like this on Render, serving media
# directly is a completely standard, well-understood tradeoff. If
# traffic grows significantly, moving uploads to a dedicated storage
# service (so the web process isn't handling file serving) is the
# natural next step.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        static_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]

# Custom error handler for the 404 page requested in the brief.
handler404 = 'jobs.views.custom_404'
