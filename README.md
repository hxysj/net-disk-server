## 个人网盘系统项目

### 项目介绍

本项目为 net-disk 的后端项目，使用 Django 框架实现，为 net-disk 项目提供 websocket 接口地址以及文件上传管理的接口地址

### netDisk 前端项目地址

```
net-disk: https://github.com/hxysj/net-disk
```

### 需要进行配置的内容

#### 配置邮箱授权信息

用来发送用户注册时的邮箱验证码

![image-20250705230751740](README.assets/image-20250705230751740.png)

#### 配置数据库地址与密码

![image-20250705230857492](README.assets/image-20250705230857492.png)

#### 配置 redis 的地址

![image-20250706141713482](README.assets/image-20250706141713482.png)

### 安装相关依赖

```
python install -r requirements.txt
```

#### 安装FFmpeg

用来进行视频切割

下载[FFmpeg](https://www.gyan.dev/ffmpeg/builds)

![image-20240918200034959](README.assets/image-20240918200034959.png)

解压FFmpeg

![image-20240918200053520](README.assets/image-20240918200053520.png)

将bin添加到环境变量

![image-20240918200259391](README.assets/image-20240918200259391.png)

检查是否安装成功

```
ffmpeg --version
```

![image-20240918200347386](README.assets/image-20240918200347386.png)

#### 安装celery

#### 安装 aspose - 有水印

```
pip install aspose
```

用来将doc文件转换成docx文件

#### 安装pycryptodome

```
pip install pycryptodome
```

用于分块文件的解密

#### 安装channels，daphne

```
pip install channels,channels_redis
pip install daphne
```

用于建立websocket连接

### 项目运行

#### 下载项目

```
git clone https://github.com/hxysj/net-disk-server.git

cd net-disk-server

```

#### 迁移数据库

在 mysql 中创建对应的数据库

![image-20241012215741640](README.assets/image-20241012215741640.png)

```
python manage.py makemigrations

python manage.py migrate
```

![image-20241012215527636](README.assets/image-20241012215527636.png)

![image-20241012215750667](netDisk-server.assets/image-20241012215750667.png)

#### 初始化数据

```
python manage.py loaddata utils/initial_data.json
```

![image-20241012220343931](README.assets/image-20241012220343931.png)

管理员： admin123

密码：111111

#### 启动 django 服务

```
python manage.py runserver
```

#### 启动 websocket 服务

终端中运行

```
daphne -b 127.0.0.1 -p 8001 netDisk.asgi:application
```

#### 通过脚本创建测试用户

在项目根目录下net-disk-server

```
python scripts/create_test_user.py
或者
PYTHONPATH=$(pwd) python scripts/create_test_user.py
```

