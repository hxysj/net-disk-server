# -*- codeing = utf-8 -*-
# @Time : 2024/9/16 22:20
# @Author : °。零碎゛記忆
# @File : logging_dec.py
# @Software : PyCharm
from django.http import JsonResponse
from django.conf import settings
from User.models import User
from FileShare.models import FileShare
import jwt
from django.core.cache import cache


def logging_check(func):
    def wrap(request, *args, **kwargs):
        # 获取token   request.META.get('HTTP_AUTHORIZATION')
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            result = {'code': 403, 'error': 'Please login'}
            return JsonResponse(result, status=401)
        # 校验token
        # 失败返回 403
        try:
            res = jwt.decode(token, settings.JWT_TOKEN_KEY, algorithms=['HS256'])
        except Exception as e:
            print('jwt decode error is %s' % e)
            result = {'code': 403, 'error': 'Please login'}
            return JsonResponse(result, status=401)

        # 解析token中的user_id
        user_id = res['uid']
        if cache.get(f'user_${user_id}'):
            user = cache.get(f'user_${user_id}')
        else:
            user = User.objects.get(user_id=user_id)
            cache.set(f'user_${user_id}', user, 60 * 60)
        request.my_user = user

        return func(request, *args, **kwargs)

    return wrap


# 检测分析链接是否输入验证码
def code_check(func):
    def wrap(request, *args, **kwargs):
        # print(request.COOKIES)
        code_token = request.COOKIES.get('check_token')
        # print(code_token)
        if not code_token:
            result = {'code': 403, 'error': 'please input the code'}
            return JsonResponse(result, status=403)
        try:
            res = jwt.decode(code_token, settings.CODE_TOKEN_KEY, algorithms='HS256')
        except Exception as e:
            print('jwt code decode error is %s' % e)
            result = {'code': 403, 'error': 'please input the code'}
            return JsonResponse(result, status=403)
        # 解析cookie中的 提取码code
        code = res['code']
        # print(code)
        share_id = res['shareId']
        # print(share_id)
        if cache.get(f'share_file_info_${share_id}'):
            share_file = cache.get(f'share_file_info_${share_id}')
            if share_file.code != code:
                result = {'code': 403, 'error': 'please input the code'}
                return JsonResponse(result, status=403)
        else:
            try:
                share_file = FileShare.objects.get(share_id=share_id, code=code)
                cache.set(f'share_file_info_${share_id}', share_file, 60 * 60)
            except Exception as e:
                print('jwt code decode error is %s' % e)
                result = {'code': 403, 'error': 'please input the code'}
                return JsonResponse(result, status=403)
        request.share_code = code

        return func(request, *args, **kwargs)

    return wrap


# 校验是否为管理员账号
def check_admin(func):
    def wrap(request, *args, **kwargs):
        # return JsonResponse({'code':200})
        user = request.my_user

        if not user.identity:
            result = {'code': 403, 'error': 'Please login'}
            return JsonResponse(result, status=401)

        return func(request, *args, **kwargs)

    return wrap
