"""
WSGI config for tkp_generator project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tkp_generator.settings')

application = get_wsgi_application()
