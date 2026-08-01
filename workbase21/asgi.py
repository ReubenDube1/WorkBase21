"""
ASGI config for WorkBase21 project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workbase21.settings')

application = get_asgi_application()
