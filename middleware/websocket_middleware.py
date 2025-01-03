import jwt
from django.conf import settings
from django.core.cache import cache
import urllib.parse
class WsTokenVerify:
    def __init__(self,app):
        self.app = app

    async def __call__(self,scope,receive,send):
        query_params = urllib.parse.parse_qs(scope['query_string'].decode())
        file_id = query_params.get('file_id',[None])[0]
        token = query_params.get('token',[None])[0]
        try:
            jwt_dict = jwt.decode(token, settings.JWT_TOKEN_KEY, algorithms=['HS256'])
        except Exception as e:
            print(f'websocket jwt is error: {e}')
            return await self.app(scope,receive,send)
        user_id = jwt_dict['uid']
        if cache.get(f'user_${user_id}'):
            user = cache.get(f'user_${user_id}')
            scope['user'] = user
        cache.set(f'file_uploader_${file_id}', True, 60*10)
        return await self.app(scope, receive, send)