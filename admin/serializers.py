# -*- codeing = utf-8 -*-
# @Time : 2024/9/22 13:29
# @Author : °。零碎゛記忆
# @File : serializers.py
# @Software : PyCharm
from rest_framework import serializers
from FileInfo.models import FileInfo
from User.models import User


class AdminFileInfoSerializer(serializers.ModelSerializer):
    fileId = serializers.CharField(source='file_id')
    filePid = serializers.CharField(source='file_pid')
    fileSize = serializers.IntegerField(source='file_size')
    fileType = serializers.IntegerField(source='file_type')
    fileCategory = serializers.IntegerField(source='file_category')
    folderType = serializers.IntegerField(source='folder_type')
    fileName = serializers.CharField(source='file_name')
    fileCover = serializers.ImageField(source='file_cover')
    lastUpdateTime = serializers.DateTimeField(source='last_update_time')
    nickName = serializers.CharField(source='user_id.nick_name')
    userId = serializers.CharField(source='user_id.user_id')

    class Meta:
        model = FileInfo
        fields = ['fileId',
                  'filePid',
                  'fileSize',
                  'fileType',
                  'fileCategory',
                  'folderType', 'status', 'fileName', 'fileCover', 'lastUpdateTime', 'status', 'nickName', 'userId']


class AdminUserSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user_id')
    nickName = serializers.CharField(source='nick_name')
    lastLoginTime = serializers.DateTimeField(source='last_login_time')
    joinTime = serializers.DateTimeField(source='create_time')
    useSpace = serializers.IntegerField(source='use_space')
    totalSpace = serializers.IntegerField(source='total_space')
    class Meta:
        model = User
        fields = ['userId', 'nickName', 'avatar', 'lastLoginTime', 'joinTime', 'useSpace', 'totalSpace', 'status']