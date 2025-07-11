"""
URL configuration for netDisk project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import csrf_token

urlpatterns = [
    path('admin/', admin.site.urls),
    # 获得csrf令牌
    path('api/csrf', csrf_token),
    path('api/', include('User.urls')),
    path('api/file/', include('FileInfo.urls')),
    path('api/recycle/', include('Recycle.urls')),
    path('api/share/', include('FileShare.urls')),
    path('api/showShare/', include('Share.urls')),
    path('api/admin/', include('admin.urls')),
    path('api/chat/', include('Chat.urls'))
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
