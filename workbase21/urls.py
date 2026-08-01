"""
URL configuration for WorkBase21 project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('jobs.urls')),
]

# Serve media files (company logos, CKEditor uploads) during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handler for the 404 page requested in the brief.
handler404 = 'jobs.views.custom_404'
