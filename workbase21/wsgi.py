"""
WSGI config for WorkBase21 project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workbase21.settings')

application = get_wsgi_application()
