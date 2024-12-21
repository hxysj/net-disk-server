# -*- codeing = utf-8 -*-
# @Time : 2024/9/22 13:17
# @Author : °。零碎゛記忆
# @File : urls.py
# @Software : PyCharm
from django.urls import path
from . import views

urlpatterns = [
    path('loadFileList', views.load_file_list),
    # 删除文件
    path('delFile', views.del_file),
    # 获得用户列表
    path('getUserList', views.get_user_list),
    # 更新用户的启用情况
    path('updateUserStatus', views.update_user_status),
    # 更新用户的空间大小
    path('updateUserSpace', views.update_user_space),
    # 获取视频的内容m3u8
    path('getVideoInfo/<str:file_user>', views.get_video_info),
    # 获取文件内容
    path('getFile/<str:file_user>', views.get_file),
    # 获取系统设置
    path('getSysSettings', views.get_sys_settings),
    # 更新系统设置
    path('updateSetting', views.update_settings),
    # 创建下载链接
    path('createDownloadUrl/<str:file_id>/<str:user_id>', views.create_download_url),
    # 文件下载
    path('download/<str:url_base64>/<str:filename>', views.download)
]