"""
URL configuration for WorkBase21 project.
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('jobs.urls')),
]

# Serve media files (job images, company logos, CKEditor uploads, Z83
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
