from django.shortcuts import render
from django.http import JsonResponse
import json
import hashlib
from .models import User, Config
import uuid
import time
import jwt
from tools.logging_dec import logging_check
import os
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
import random
import string
from django.http import JsonResponse
from django.conf import settings
from utils.utils import generate_captcha

responseData = {
    'code': 200,
    'data': [],
    'error': 'null'
}


# 生成token
def make_token(username, user_id, avatar, identity, expire=3600 * 24):
    key = settings.JWT_TOKEN_KEY
    now_time = time.time()
    payload_data = {
        'username': username,
        'avatar': avatar,
        'uid': user_id,
        'identity': identity,
        'exp': now_time + expire
    }
    return jwt.encode(payload_data, key, algorithm='HS256')


# 视图函数：生成验证码并返回给前端
def captcha_image(request):
    captcha_text, img_base64 = generate_captcha()

    # 生成一个唯一的 ID（可以是 UUID 或随机字符串）
    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # 将验证码文本存入 Redis，设置过期时间（如 5 分钟）
    cache.set(f'captcha:{captcha_id}', captcha_text, 300)

    # 返回生成的验证码 ID 和图像的 Base64 数据
    return JsonResponse({'captcha_id': captcha_id, 'captcha_image': img_base64})


# 验证用户输入的验证码
def captcha_verify(request):
    # print(request.POST)
    data = json.loads(request.body)
    user_input = data.get('captcha_code')
    captcha_id = data.get('captcha_id')

    # 从 Redis 中获取验证码文本
    captcha_text = cache.get(f'captcha:{captcha_id}')

    if not captcha_text:
        return JsonResponse({'message': '验证码已过期或无效'}, status=301)

    # 验证用户输入的验证码与 Redis 中存储的验证码
    if user_input and user_input.lower() == captcha_text.lower():
        return JsonResponse({'status': 'success', 'message': '验证码验证成功'})
    else:
        return JsonResponse({'message': '验证码错误'}, status=301)


# 登陆功能
def login(request):
    name = request.GET.get('userName')
    password = request.GET.get('password')
    remember = request.GET.get('remember', False)
    try:
        user = User.objects.get(nick_name=name, status=True)
    except Exception as e:
        # 如果没有找到用户，则登陆失败
        return JsonResponse(
            {'code': 500, 'data': [], 'error': '用户名或密码错误！'}
        )
    pwd = hashlib.md5()
    pwd.update(password.encode())

    if pwd.hexdigest() == user.password:
        # 校验通过，用户登陆成功
        # 获取当前时间
        now = timezone.now()
        user.last_login_time = now
        user.save()
        if remember:
            # 如果用户勾选了记住我，则保存token7天，否则保持1天
            token = make_token(user.nick_name, user.user_id, user.avatar.name, user.identity, 60 * 60 * 24 * 7)
        else:
            token = make_token(user.nick_name, user.user_id, user.avatar.name, user.identity)
        cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
        return JsonResponse(
            {
                'code': 200,
                'data': {
                    'token': token
                }
            }
        )
    return JsonResponse(
        {'code': 500, 'error': '用户名或密码错误！'}
    )


# 发送邮箱验证码
def send_email_code(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': '发送失败！'
        }, status=500)
    email = json.loads(request.body).get('email')
    print(email)
    import random
    str1 = '0123456789abcdefghijklmnopqrstuvwxyz'
    rand_str = ''
    for i in range(0, 6):
        rand_str += str1[random.randrange(0, len(str1))]
    message = "您的验证码是：" + rand_str + ', 10分钟内有效，请尽快填写！'
    subject = '验证码'
    # emailBox = []
    # emailBox.append(email)
    # 发送邮件
    res = send_mail(subject, message, '2413867596@qq.com', [email])
    if res == 1:
        cache.set(f'email_code_${email}', rand_str, 60 * 10)
        return JsonResponse({
            'status': 'success'
        })
    else:
        return JsonResponse({
            'error': '发送失败！'
        }, status=500)
    # print(emailBox)


# 注册功能
def register(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': '注册失败'
        }, status=500)
    # print(request.POST['userName'])
    pwd = hashlib.md5()
    data = json.loads(request.body)
    name = data.get('userName')
    password = data.get('password')
    email = data.get('email')
    code = data.get('code')
    if cache.get(f'email_code_${email}'):
        if code != cache.get(f'email_code_${email}'):
            return JsonResponse({
                'error': '注册失败，邮箱验证码错误或失效！'
            }, status=500)
    else:
        return JsonResponse({
            'error': '注册失败，邮箱验证码错误或失效！'
        }, status=500)
    pwd.update(password.encode())
    uid = uuid.uuid4()
    print(uid)
    # 查找是否有相同的邮箱存在
    same_email = User.objects.filter(email=email)
    if len(same_email) != 0:
        return JsonResponse({
            'error': '注册失败，邮箱已被使用！'
        }, status=500)
    try:
        config = Config.objects.get(config_id='netdiskconfig')
        User.objects.create(user_id=uid, nick_name=name, password=pwd.hexdigest(), email=email,
                            total_space=config.user_space)
    except Exception as e:
        print('register is error: ', e)
        return JsonResponse({
            'error': '注册失败，用户名已存在!'
        }, status=500)
    responseData['code'] = 200
    responseData['error'] = 'null'
    return JsonResponse(responseData)


# 找回密码 - 未登录时
def retrieve_password(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': "retrieve password is error"
        }, status=500)
    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')
    code = data.get('code')
    if cache.get(f'email_code_${email}'):
        if code != cache.get(f'email_code_${email}'):
            return JsonResponse({
                'error': '注册失败，邮箱验证码错误或失效！'
            }, status=500)
    else:
        return JsonResponse({
            'error': '注册失败，邮箱验证码错误或失效！'
        }, status=500)
    pwd = hashlib.md5()
    pwd.update(password.encode())
    try:
        user = User.objects.get(email=email)
    except Exception as e:
        return JsonResponse({
            'error': '修改失败，账号不存在！'
        }, status=500)
    user.password = pwd.hexdigest()
    user.save()
    cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
    return JsonResponse({
        'status': 'success',
        'code': 200
    })


# 修改密码
@logging_check
def updatePassword(request):
    # 判断是否为pos请求
    if request.method == 'POST':
        body = json.loads(request.body)
        user = request.my_user
        # 获取请求的请求体中的密码
        newPwd = body.get('password')
        pwd = hashlib.md5()
        pwd.update(newPwd.encode())
        # 设置新的密码
        user.password = pwd.hexdigest()
        user.save()
        cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
        result = {
            'code': 200,
            'msg': '密码修改成功！'
        }
        return JsonResponse(result)
    else:
        return JsonResponse({
            'code': 404,
            'error': 'update password is wrong'
        })


# 上传用户头像
@logging_check
def updateAvatar(request):
    if request.method != 'POST' or not request.FILES['image']:
        return JsonResponse({
            'code': 404,
            'error': 'request is wrong'
        })
    # 获取用户上传的文件
    new_avatar = request.FILES['image']
    user = request.my_user
    # 获取用户的旧头像
    old_avatar = user.avatar.name
    # 更改用户头像
    user.avatar = new_avatar
    user.save()
    # 更新用户的缓存
    cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
    # 删除原来的头像，不删除默认的头像
    if old_avatar != 'avatar/default.png':
        try:
            os.remove(settings.MEDIA_ROOT + '/' + old_avatar)
        except Exception as e:
            print('remove old file is error: %s' % e)

    # 更新头像后要生成新的token
    token = make_token(user.nick_name, user.user_id, user.avatar.name, user.identity)
    result = {
        'code': 200,
        'data': {
            'token': token
        }
    }
    return JsonResponse(result)


# 获得用户的使用空间和总空间
@logging_check
def get_user_space(request):
    user = request.my_user
    return JsonResponse({
        'code': 200,
        'data': {
            'totalSpace': user.total_space,
            'useSpace': user.use_space
        }
    })
