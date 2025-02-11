import jwt
from django.conf import settings
from django.core.cache import cache
import os
import django
from asgiref.sync import sync_to_async

# 手动设置 Django 配置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netDisk.settings')
django.setup()
from User.models import User
import urllib.parse


class WsTokenVerify:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_params = urllib.parse.parse_qs(scope['query_string'].decode())
        file_id = query_params.get('file_id', [None])[0]
        token = query_params.get('token', [None])[0]
        try:
            jwt_dict = jwt.decode(token, settings.JWT_TOKEN_KEY, algorithms=['HS256'])
        except Exception as e:
            print(f'websocket jwt is error: {e}')
            return await self.app(scope, receive, send)
        user_id = jwt_dict['uid']
        user = cache.get(f'user_${user_id}')
        if user:
            user = await self.get_user(user_id)
            cache.set(f'user_${user_id}', user, 60 * 60 * 1)
        scope['user'] = user
        cache.set(f'file_uploader_${file_id}', 1, 60 * 10)
        return await self.app(scope, receive, send)

    @sync_to_async
    def get_user(self, user_id):
        """同步执行数据库查询，避免 SynchronousOnlyOperation 错误"""
        return User.objects.get(user_id=user_id)
