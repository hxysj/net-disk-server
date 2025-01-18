from email.policy import default

from django.db import models
from User.models import User
from FileInfo.models import FileInfo


# Create your models here.

class ConverSations(models.Model):
    conversation_id = models.CharField('会话id', max_length=40, primary_key=True, unique=True)
    create_time = models.DateTimeField('创建会话时间', auto_now_add=True)
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user1_conversations')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user2_conversations')
    user1_delete_at = models.DateTimeField('删除记录的时间', null=True, blank=True)
    user2_delete_at = models.DateTimeField('删除记录的时间', null=True, blank=True)

    class Meta:
        db_table = 'conversations'


class ConverSationsUser(models.Model):
    conversation_id = models.ForeignKey(ConverSations, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    join_time = models.DateTimeField('加入会话时间', auto_now_add=True)

    class Meta:
        db_table = 'conversations_user'


class Message(models.Model):
    message_id = models.CharField('消息id', max_length=40, primary_key=True, unique=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation_id = models.ForeignKey(ConverSations, on_delete=models.CASCADE)
    create_time = models.DateTimeField('创建消息时间', auto_now_add=True)
    content = models.CharField('消息内容', max_length=200, null=True)
    file_id = models.ForeignKey(FileInfo, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.IntegerField('消息已读状态', default=0)

    class Meta:
        db_table = 'message'
