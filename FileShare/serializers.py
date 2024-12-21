# -*- codeing = utf-8 -*-
# @Time : 2024/9/17 21:59
# @Author : °。零碎゛記忆
# @File : serializers.py
# @Software : PyCharm
from rest_framework import serializers
from FileShare.models import FileShare


class shareSerializer(serializers.ModelSerializer):
    shareId = serializers.CharField(source='share_id')
    shareTime = serializers.DateTimeField(source='share_time')
    showCount = serializers.IntegerField(source='show_count')
    expireTime = serializers.DateTimeField(source='expire_time')
    fileCategory = serializers.IntegerField(source='file_id.file_category')
    fileCover = serializers.ImageField(source='file_id.file_cover')
    fileId = serializers.CharField(source='file_id.file_id')
    folderType = serializers.IntegerField(source='file_id.folder_type')
    fileName = serializers.CharField(source='file_id.file_name')
    fileType = serializers.IntegerField(source='file_id.file_type')

    class Meta:
        model = FileShare
        fields = ['shareId',
                  'shareTime',
                  'showCount',
                  'code', 'expireTime', 'fileCategory', 'fileCover', 'fileId', 'folderType', 'fileName', 'fileType']
