from rest_framework import serializers
from User.models import User, Friend


class friendSerializer(serializers.ModelSerializer):
    userId1 = serializers.CharField(source='user1.user_id')
    userId2 = serializers.CharField(source='user2.user_id')
    userName1 = serializers.CharField(source='user1.nick_name')
    userName2 = serializers.CharField(source='user2.nick_name')
    userAvatar1 = serializers.ImageField(source='user1.avatar')
    userAvatar2 = serializers.ImageField(source='user2.avatar')
    f_id = serializers.CharField(source='friend_id')

    class Meta:
        model = Friend
        fields = ['f_id', 'userId1', 'userId2', 'userName1', 'userName2', 'userAvatar1', 'userAvatar2', 'status']


class FriendListSerializer(serializers.ModelSerializer):
    f_id = serializers.CharField(source='friend_id')

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # 获取传入的 user 参数
        user = self.context.get('user')
        if user:
            if instance.user1 == user:
                representation['nick_name'] = instance.user2.nick_name
                representation['avatar'] = instance.user2.avatar.url
                representation['uid'] = instance.user2.user_id
                representation['email'] = instance.user2.email
            elif instance.user2 == user:
                representation['nick_name'] = instance.user1.nick_name
                representation['avatar'] = instance.user1.avatar.url
                representation['uid'] = instance.user1.user_id
                representation['email'] = instance.user1.email
        return representation

    class Meta:
        model = Friend
        fields = ['f_id']
