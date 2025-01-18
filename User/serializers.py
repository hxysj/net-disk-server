from rest_framework import serializers
from User.models import User, Friend


class friendSerializer(serializers.ModelSerializer):
    userId1 = serializers.CharField(source='user1.user_id')
    userId2 = serializers.CharField(source='user2.user_id')
    userName1 = serializers.CharField(source='user1.nick_name')
    userName2 = serializers.CharField(source='user2.nick_name')
    userAvatar1 = serializers.ImageField(source='user1.avatar')
    userAvatar2 = serializers.ImageField(source='user2.avatar')

    class Meta:
        model = Friend
        fields = ['userId1', 'userId2', 'userName1', 'userName2', 'userAvatar1', 'userAvatar2', 'status']
