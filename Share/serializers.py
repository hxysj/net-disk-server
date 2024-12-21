# -*- codeing = utf-8 -*-
# @Time : 2024/9/17 21:59
# @Author : °。零碎゛記忆
# @File : serializers.py
# @Software : PyCharm
from rest_framework import serializers
from FileShare.models import FileShare


class webShareSerializer(serializers.ModelSerializer):
    shareId = serializers.CharField(source='share_id')
    shareTime = serializers.DateTimeField(source='share_time')
    fileName = serializers.CharField(source='file_id.file_name')
    nickName = serializers.CharField(source='user_id.nick_name')
    avatar = serializers.ImageField(source='user_id.avatar')
    userId = serializers.CharField(source='user_id.user_id')
    filePid = serializers.CharField(source='file_id.file_pid')

    class Meta:
        model = FileShare
        fields = ['shareId',
                  'shareTime',
                  'fileName', 'nickName', 'avatar', 'userId', 'filePid']
