from django.urls import path
from .consumers import FileTransferConsumer, ChatMessageConsumer

websocket_urlpatterns = [
    path(r'ws/file/', FileTransferConsumer.as_asgi()),
    path(r'ws/message/<str:conversation_id>/', ChatMessageConsumer.as_asgi())
]
