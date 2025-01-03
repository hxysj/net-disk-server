from django.urls import path
from .consumers import FileTransferConsumer

websocket_urlpatterns = [
    path(r'ws/file/',FileTransferConsumer.as_asgi())
]