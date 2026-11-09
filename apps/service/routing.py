from django.urls import path

from apps.service.assistant.consumers import AssistantConsumer

websocket_urlpatterns = [
    path("ws/assistant/", AssistantConsumer.as_asgi()),
]
