import os
import django
import hashlib
import re
from faker import Faker
from django.utils import timezone

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netDisk.settings')
django.setup()

from User.models import User, Config  # 替换为你的应用名和模型

# 初始化Faker
fake = Faker()


def md5_encrypt(password):
    """
    使用MD5加密密码
    :param password: 明文密码
    :return: MD5加密后的密码
    """
    md5 = hashlib.md5()
    md5.update(password.encode('utf-8'))
    return md5.hexdigest()


def generate_username():
    """
    生成符合要求的用户名（3-9位字母或数字）
    :return: 符合条件的用户名
    """
    while True:
        # 使用Faker生成一个随机用户名
        username = fake.user_name()
        # 过滤掉不符合条件的字符（只保留字母和数字）
        username = re.sub(r'[^a-zA-Z0-9]', '', username)
        # 确保用户名长度在3到9位之间
        if 3 <= len(username) <= 9:
            return username


def create_test_users(num_users):
    """
    批量创建测试用户
    :param num_users: 需要创建的用户数量
    """
    # 获取默认的用户空间配置
    config = Config.objects.first()
    if not config:
        config = Config.objects.create(
            config_id='default_config',
            user_space=10737418240  # 默认10GB空间
        )

    for _ in range(num_users):
        user_id = fake.uuid4()  # 生成唯一的用户ID
        nick_name = generate_username()  # 生成符合要求的用户名
        email = fake.email()  # 生成随机邮箱
        password = '123456'  # 统一密码
        encrypted_password = md5_encrypt(password)  # MD5加密密码
        avatar = 'avatar/default.png'  # 默认头像
        create_time = timezone.now()  # 当前时间
        last_login_time = None  # 初始化为空
        status = True  # 默认启用
        use_space = 0  # 初始已使用空间为0
        total_space = config.user_space  # 使用配置中的默认空间
        identity = False  # 默认身份为普通用户

        # 创建用户
        user = User.objects.create(
            user_id=user_id,
            nick_name=nick_name,
            email=email,
            password=encrypted_password,  # 存储加密后的密码
            avatar=avatar,
            create_time=create_time,
            last_login_time=last_login_time,
            status=status,
            use_space=use_space,
            total_space=total_space,
            identity=identity
        )

        # 输出用户的账号和密码
        print(f'创建用户成功: 账号={nick_name}, 邮箱={email}, 密码={password}')


if __name__ == '__main__':
    # 交互式询问用户需要创建的数据条数
    while True:
        try:
            num_users = int(input("请输入需要创建的测试用户数量: "))
            if num_users <= 0:
                print("请输入一个大于0的正整数！")
            else:
                break
        except ValueError:
            print("请输入一个有效的整数！")

    # 调用函数创建用户
    create_test_users(num_users)
    print(f'成功创建 {num_users} 个测试用户！')
