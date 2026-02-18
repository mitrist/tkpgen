"""
ASGI config for tkp_generator project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tkp_generator.settings')

application = get_asgi_application()
