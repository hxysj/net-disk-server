from django.urls import path
from . import views

urlpatterns = [
    path('getSession', views.get_session),
    path('getMessage', views.get_message),
    path('addNewSession', views.create_session),
    path('setMessageRead', views.set_read_message),
    path('clearChatRecord', views.clear_chat_record)
]
