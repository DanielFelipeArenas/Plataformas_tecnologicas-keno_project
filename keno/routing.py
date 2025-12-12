from django.urls import path
from . import consumer

websocket_urlpatterns = [
    path('ws/game/', consumer.GameConsumer.as_asgi()),
    path('ws/sala/<str:sala_id>/', consumer.SalaConsumer.as_asgi()),
]