"""
ASGI config: plain HTTP (Django) + the WebSocket of the AI assistant (Django Channels).

On prod gunicorn (WSGI) keeps serving HTTP; a separate daphne process serves `/ws/`.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django has to be set up before the routing imports models
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from apps.service.routing import websocket_urlpatterns  # noqa: E402

# No origin check: the app sends no Origin and the site is on another host (HTTP allows every origin too —
# CORS_ALLOW_ALL_ORIGINS); the customer is known by the token in the query string, never by a cookie.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(websocket_urlpatterns),
})
