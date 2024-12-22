# -*- codeing = utf-8 -*-
# @Time : 2024/9/16 16:48
# @Author : °。零碎゛記忆
# @File : urls.py
# @Software : PyCharm
from django.urls import path
from . import views

urlpatterns = [
    # 登录
    path('login', views.login),
    # 发送邮箱验证码
    path('sendEmailCode', views.send_email_code),
    # 注册
    path('register', views.register),
    # 更改用户头像
    path('updateAvatar', views.updateAvatar),
    # 更改用户密码
    path('updatePassword', views.updatePassword),
    # 获取用户空间情况
    path('getUserSpace', views.get_user_space),
    # 找回密码
    path('RetrievePassword', views.retrieve_password),
    # 获取图形校验码
    path('getVerificationCode', views.captcha_image),
    # 校验验证码
    path('checkVerificationCode', views.captcha_verify)
]