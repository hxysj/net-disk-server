# -*- codeing = utf-8 -*-
# @Time : 2024/9/17 21:59
# @Author : °。零碎゛記忆
# @File : serializers.py
# @Software : PyCharm
from rest_framework import serializers
from FileInfo.models import FileInfo


class recycleSerializer(serializers.ModelSerializer):
    fileId = serializers.CharField(source='file_id')
    fileSize = serializers.IntegerField(source='file_size')
    fileType = serializers.IntegerField(source='file_type')
    fileCategory = serializers.IntegerField(source='file_category')
    folderType = serializers.IntegerField(source='folder_type')
    fileName = serializers.CharField(source='file_name')
    fileCover = serializers.ImageField(source='file_cover')
    recoveryTime = serializers.DateTimeField(source='recovery_time')

    class Meta:
        model = FileInfo
        fields = ['fileId',
                  'fileSize',
                  'fileType',
                  'fileCategory',
                  'folderType','fileName','fileCover','recoveryTime']
