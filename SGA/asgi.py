"""
ASGI config for SGA project.

Configures ASGI application with Django Channels for WebSocket support.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Import WebSocket URL patterns (will be created)
try:
    from ARQUIVOS.routing import websocket_urlpatterns
except ImportError:
    websocket_urlpatterns = []

application = ProtocolTypeRouter({
    # HTTP requests are handled by Django's ASGI application
    "http": django_asgi_app,
    
    # WebSocket requests are handled by Channels
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
