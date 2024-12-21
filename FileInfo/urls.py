# -*- codeing = utf-8 -*-
# @Time : 2024/9/17 16:22
# @Author : °。零碎゛記忆
# @File : urls.py
# @Software : PyCharm
from django.urls import path,re_path
from . import views

urlpatterns = [
    # 获得首页的数据
    path('loadDataList', views.loadDataList),
    # 新建文件夹
    path('newFoloder', views.newFoloder),
    # 获得文件的信息
    path('getFolderInfo', views.get_folder_info),
    # 重命名
    path('rename', views.rename),
    # 获取移动文件的目录
    path('getCurrentList', views.get_current_list),
    # 移动文件到对应目录
    path('moveFile', views.change_file_folder),
    # 删除文件,进入回收站
    path('delFile', views.del_file),
    # 上传文件
    path('uploadFile', views.upload_file),
    # 获取视频的内容m3u8
    path('getVideoInfo/<str:file_id>', views.get_video_info),
    # 获取文件内容
    path('getFile/<str:file_id>', views.get_file),
    # 取消上传
    path('cancelUpload', views.cancel_uploader),
    # 创建下载链接
    path('createDownloadUrl/<str:file_id>', views.create_download_url),
    # 下载文件
    path('download/<str:url_base64>/<str:filename>', views.download)
]

