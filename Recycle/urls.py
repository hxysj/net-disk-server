# -*- codeing = utf-8 -*-
# @Time : 2024/9/19 20:21
# @Author : °。零碎゛記忆
# @File : urls.py
# @Software : PyCharm
from django.urls import path
from . import views

urlpatterns = [
    # 获得回收站的文件
    path('loadRecycleList', views.load_recycle_list),
    # 还原进入回收站的文件
    path('recoverFile', views.recover_file),
    # 彻底删除文件
    path('delFile', views.delete_file)
]