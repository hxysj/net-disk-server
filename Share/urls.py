# -*- codeing = utf-8 -*-
# @Time : 2024/9/20 19:30
# @Author : °。零碎゛記忆
# @File : urls.py
# @Software : PyCharm
from django.urls import path
from . import views

urlpatterns = [
    # 获得分享的基础信息
    path('getShareInfo/<str:share_id>', views.get_share_file),
    # 获得分享的文件信息
    path('loadFileList', views.load_file_list),
    # 校验提取码
    path('checkShareCode', views.check_code),
    # 检测是否登录
    path('checkLogin', views.check_login),
    # 保存到我的网盘
    path('saveShare', views.save_share),
    # 获得文件信息
    path('getFile/<str:file_id>', views.get_file),
    # 获取视频信息
    path('getVideoInfo/<str:file_id>', views.get_video_info),
    # 创建下载链接
    path('createDownloadUrl/<str:file_id>', views.create_download_url),
    # 下载文件
    path('download/<str:url_base64>/<str:filename>', views.download)
]

