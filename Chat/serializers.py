from rest_framework import serializers
from .models import ConverSations, ConverSationsUser, Message


class ConverSationsUserSerializers(serializers.ModelSerializer):
    user1_name = serializers.CharField(source='conversation_id.user1.nick_name')
    user1_id = serializers.CharField(source='conversation_id.user1.user_id')
    user1_avatar = serializers.CharField(source='conversation_id.user1.avatar')
    user2_name = serializers.CharField(source='conversation_id.user2.nick_name')
    user2_id = serializers.CharField(source='conversation_id.user2.user_id')
    user2_avatar = serializers.CharField(source='conversation_id.user2.avatar')
    conversation_id = serializers.CharField(source='conversation_id.conversation_id')

    class Meta:
        model = ConverSationsUser
        fields = ['user1_name', 'user1_id', 'user1_avatar', 'user2_name', 'user2_id', 'user2_avatar', 'conversation_id']


class MessageSerializers(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user_id.user_id')
    session_id = serializers.CharField(source='conversation_id')
    avatar = serializers.CharField(source='user_id.avatar')
    nick_name = serializers.CharField(source='user_id.nick_name')

    class Meta:
        model = Message
        fields = ['message_id', 'user_id', 'session_id', 'create_time', 'content', 'avatar', 'nick_name', 'create_time']
