# -*- codeing = utf-8 -*-
# @Time : 2024/9/19 23:03
# @Author : °。零碎゛記忆
# @File : urls.py
# @Software : PyCharm
from django.urls import path
from . import views

urlpatterns = [
    path('loadShareList', views.load_share_file),
    path('shareFile', views.share_file),
    path('cancelShare', views.cancel_share)
]