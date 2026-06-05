from django.urls import path
from apps.gestion.consumers import TableroConsumer

websocket_urlpatterns = [
    path("ws/tablero/", TableroConsumer.as_asgi()),
]
