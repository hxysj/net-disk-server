from email.policy import default

from django.db import models


class User(models.Model):
    user_id = models.CharField('用户id', max_length=40, primary_key=True, unique=True)
    nick_name = models.CharField('用户昵称', max_length=15, unique=True)
    email = models.EmailField('用户邮箱', unique=True)
    password = models.CharField('用户密码', max_length=32)
    avatar = models.FileField('用户头像', upload_to='avatar', default='avatar/default.png')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    last_login_time = models.DateTimeField('最后登陆时间', null=True)
    status = models.BooleanField('用户状态', default=True)
    use_space = models.BigIntegerField('已使用空间', default=0)
    total_space = models.BigIntegerField('总空间', default=0)
    identity = models.BooleanField('身份', default=False)

    class Meta:
        db_table = 'user'


class Config(models.Model):
    config_id = models.CharField('设置的id', max_length=32, primary_key=True, unique=True)
    user_space = models.BigIntegerField('用户的默认空间大小')

    class Meta:
        db_table = 'config'


# user1 作为发起添加好友的用户
# user2 作为接收是否添加好友的用户
# status 状态： 0待通过 1拒接 2通过
class Friend(models.Model):
    friend_id = models.AutoField(primary_key=True)
    user1 = models.ForeignKey(User, related_name='friend_user1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friend_user2', on_delete=models.CASCADE)
    status = models.IntegerField('状态', default=0)

    class Meta:
        db_table = 'friend'
