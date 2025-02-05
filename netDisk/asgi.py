"""
ASGI config for netDisk project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter,URLRouter
from middleware.websocket_middleware import WsTokenVerify
from netDisk.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netDisk.settings')

application = ProtocolTypeRouter({
    "http":get_asgi_application(),
    "websocket":WsTokenVerify(
        AuthMiddlewareStack(URLRouter(
            websocket_urlpatterns
        ))
    )
})
