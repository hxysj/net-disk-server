import math
from shutil import disk_usage

from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from tools.logging_dec import check_admin, logging_check
from FileInfo.models import FileInfo
import json
from .serializers import AdminFileInfoSerializer, AdminUserSerializer
from User.models import User, Config
import os
from django.conf import settings
import base64
from cryptography.fernet import Fernet
from django.core.files.storage import default_storage
import subprocess
from django.core.cache import cache
from django.db.models import Q
import shutil


# 获得文件信息
@logging_check
@check_admin
def load_file_list(request):
    if request.method != 'POST':
        return JsonResponse({
            'message': 'get file is error'
        }, status=404)
    request_data = json.loads(request.body)
    pid = request_data.get('pid')
    fuzzy = request_data.get('fileNameFuzzy', False)
    page_now = int(request_data.get('pageNo'))
    page_size = int(request_data.get('pageSize'))
    filters = Q(file_pid=pid, del_flag=2)
    if fuzzy:
        filters &= Q(file_name__icontains=fuzzy)
    try:
        file_list = FileInfo.objects.filter(filters).order_by('-last_update_time')[
                    (page_now - 1) * page_size:page_now * page_size]
        total_num = FileInfo.objects.filter(filters).count()
    except Exception as e:
        print('get file is error: %s' % e)
        return JsonResponse({
            'message': 'get file is error',
        }, status=4000)
    data = AdminFileInfoSerializer(file_list, many=True).data
    return JsonResponse({
        'pageNo': page_now,
        'pageSize': page_size,
        'pageTotal': math.ceil(total_num / page_size),
        'list': data
    })


# 删除文件 - 彻底删除
@logging_check
@check_admin
def del_file(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'del file is error'
        }, status=404)
    request_data = json.loads(request.body)
    del_list = request_data.get('delList')
    for ls in del_list:
        if cache.get(f'user_${ls["user_id"]}'):
            user = cache.get(f'user_${ls["user_id"]}')
        else:
            try:
                user = User.objects.get(user_id=ls['user_id'])
            except Exception as e:
                print(e)
                return JsonResponse({
                    'error': 'del file is error'
                }, status=404)
        if cache.get(f'file_info_${ls["file_id"]}'):
            file = cache.get(f'file_info_${ls["file_id"]}')
        else:
            try:
                file = FileInfo.objects.get(file_id=ls['file_id'], user_id=user)
            except Exception as e:
                print(e)
                return JsonResponse({
                    'error': 'del file is error'
                }, status=404)
        # print(file.file_size, user.use_space)
        if file.file_size:
            user.use_space = user.use_space - file.file_size
            user.save()
            cache.set(f'user_${ls["user_id"]}', user, 60 * 60 * 24)
        file.delete()
        cache.delete(f'file_info_${ls["file_id"]}')
    return JsonResponse({
        'code': 200,
        'status': 'success'
    })


# 获得视频的内容，进行预览
# @check_admin
def get_video_info(request, file_user):
    # 判断是获取m3u8文件还是读取具体的文件内容
    if file_user.endswith('.ts'):
        # print(file_id)
        media_dir = str(settings.MEDIA_ROOT)
        with open(os.path.join(media_dir, 'file', file_user), 'rb') as f:
            ts_file_content = f.read()
        return HttpResponse(ts_file_content, content_type='application/octet-stream')
    file_id = file_user.split('*usid*')[0]
    user_id = file_user.split('*usid*')[1]
    if cache.get(f'file_info_${file_id}'):
        video = cache.get(f'file_info_${file_id}')
    else:
        try:
            if cache.get(f'user_${user_id}'):
                user = cache.get(f'user_${user_id}')
            else:
                user = User.objects.get(user_id=user_id)
            video = FileInfo.objects.get(file_id=file_id, user_id=user)
            cache.set(f'file_info_${file_id}', video, 60 * 60 * 24)
        except Exception as e:
            print('get video is error: %s' % e)
            return JsonResponse({
                'code': 404,
                'error': 'get video is error'
            }, status=404)
    video_file = video.file_path.read()
    # print(type(video_file))
    return HttpResponse(video_file, content_type='application/octet-stream')


# 获取文件内容
# @check_admin
def get_file(request, file_user):
    file_id = file_user.split('*usid*')[0]
    user_id = file_user.split('*usid*')[1]
    if cache.get(f'file_info_${file_id}'):
        file = cache.get(f'file_info_${file_id}')
    else:
        try:
            if cache.get(f'user_${user_id}'):
                user = cache.get(f'user_${user_id}')
            else:
                user = User.objects.get(user_id=user_id)
            file = FileInfo.objects.get(file_id=file_id, user_id=user)
            cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
        except Exception as e:
            print('get file is error: %s' % e)
            return JsonResponse({
                'data': 'get file is error'
            }, status=500)
    file_content = file.file_path.read()
    return HttpResponse(file_content, content_type='application/octet-stream')


# 获取用户列表 - 管理员不获取，只获取普通用户
@logging_check
@check_admin
def get_user_list(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'get user list is error'
        }, status=404)
    request_data = json.loads(request.body)
    userNameFuzzy = request_data.get('userNameFuzzy', 'not_search')
    status = request_data.get('status', 'not_search')

    page_now = int(request_data.get('pageNo'))
    page_size = int(request_data.get('pageSize'))

    filters = Q(identity=False)
    if userNameFuzzy != 'not_search':
        filters &= Q(nick_name__icontains=userNameFuzzy)

    if status != 'not_search':
        filters &= Q(status=status)

    try:
        user_list = User.objects.filter(filters)[(page_now - 1) * page_size:page_now * page_size]
        total_num = User.objects.filter(filters).count()
    except Exception as e:
        print('get user list is error: %s' % e)
        return JsonResponse({
            'error': 'get user list is error'
        }, status=404)

    data = AdminUserSerializer(user_list, many=True).data

    return JsonResponse({
        'pageNo': page_now,
        'pageSize': page_size,
        'pageTotal': math.ceil(total_num / page_size),
        'list': data
    })


# 更改用户的禁用状态，默认是启用True - status
@logging_check
@check_admin
def update_user_status(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'update user status is error'
        }, status=404)
    request_data = json.loads(request.body)
    # 更改后的状态
    status = request_data.get('status')
    # 要修改的用户id
    user_id = request_data.get('userId')
    if cache.get(f'user_${user_id}'):
        user = cache.get(f'user_${user_id}')
    else:
        try:
            user = User.objects.get(user_id=user_id)
        except Exception as e:
            print(e)
            return JsonResponse({
                'error': 'update user status is error'
            }, status=404)
    user.status = status
    user.save()
    cache.set(f'user_${user_id}', user, 60 * 60 * 24)
    return JsonResponse({
        'status': 'success',
        'code': 200
    })


# 更改用户的总空间大小
@logging_check
@check_admin
def update_user_space(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'update user space is error'
        }, status=404)
    request_data = json.loads(request.body)
    user_id = request_data.get('userId')
    space = request_data.get('space')
    if cache.get(f'user_${user_id}'):
        user = cache.get(f'user_${user_id}')
    else:
        try:
            user = User.objects.get(user_id=user_id)
        except Exception as e:
            print(e)
            return JsonResponse({
                'error': 'update user space is error'
            }, status=404)
    user.total_space = space
    user.save()
    cache.set(f'user_${user_id}', user, 60 * 60 * 24)
    return JsonResponse({
        'code': 200,
        'status': 'success'
    })


# 获得系统的设置
@logging_check
@check_admin
def get_sys_settings(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'get user default space is error'
        }, status=404)
    if cache.get('system_setting'):
        config = cache.get('system_setting')
    else:
        try:
            config = Config.objects.get(config_id='netdiskconfig')
            cache.set('system_setting', config, 60 * 60 * 24)
        except Exception as e:
            print(e)
            return JsonResponse({
                'error': 'get user defautl space is error'
            }, status=404)
    #
    disk_usage = shutil.disk_usage('/')
    space = config.user_space
    return JsonResponse({
        'status': 'success',
        'useInitUseSpace': space,
        'sys_total': disk_usage.total,
        'sys_used': disk_usage.used,
        'sys_free': disk_usage.free
    })


# 更新系统设置
@logging_check
@check_admin
def update_settings(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'update setting is error'
        }, status=500)
    request_body = json.loads(request.body)
    user_space = request_body.get('useInitUseSpace')
    if cache.get('system_setting'):
        config = cache.get('system_setting')
    else:
        try:
            config = Config.objects.get(config_id='netdiskconfig')
        except Exception as e:
            print(e)
            return JsonResponse({
                'error': 'update setting is error'
            }, status=500)
    config.user_space = user_space
    config.save()
    cache.set('system_setting', config, 60 * 60 * 24)
    return JsonResponse({
        'code': 200,
        'status': 'success'
    })


# 实现文件下载功能 - 获得文件下载链接
@logging_check
@check_admin
def create_download_url(request, file_id, user_id):
    cipher_suite = Fernet(settings.FERNET_KEY)

    if request.method != 'GET':
        return JsonResponse({
            'error': 'create file download url is error'
        }, status=404)

    try:
        if cache.get(f'user_${user_id}'):
            user = cache.get(f'user_${user_id}')
        else:
            user = User.objects.get(user_id=user_id)
            cache.set(f'user_${user_id}', user, 60 * 60 * 24)
        if cache.get(f'file_info_${file_id}'):
            file = cache.get(f'file_info_${file_id}')
        else:
            file = FileInfo.objects.get(file_id=file_id, user_id=user)
            cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
    except Exception as e:
        print(e)
        return JsonResponse({
            'error': 'create file download url is error'
        })
    file_path = file.file_path
    file_url = default_storage.url(file_path).encode('utf-8')
    # print(file_url)
    data = base64.b64encode(cipher_suite.encrypt(file_url)).decode('utf-8')
    # print(data)
    return JsonResponse({
        'data': data,
        'status': 'success',
        'fileName': file.file_name,
        'code': 200
    })


def download(request, url_base64, filename):
    cipher_suite = Fernet(settings.FERNET_KEY)
    if request.method != 'GET':
        return JsonResponse({
            'error': 'download file is error'
        }, status=404)
    url_data = base64.b64decode(url_base64.encode('utf-8'))
    file_url = cipher_suite.decrypt(url_data).decode('utf-8')
    file_path = str(settings.BASE_DIR) + file_url
    # print(settings.BASE_DIR,file_path,file_url)
    if not os.path.exists(file_path):
        print('not found the file')
        return JsonResponse({
            'error': 'download file is error'
        }, status=404)

    # 分块读取文件
    def file_iterator(filepath, deleteFile=False, chunk_size=512):
        # print(filepath)
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                yield chunk
        if deleteFile:
            os.remove(filepath)

    if not file_path.endswith('.m3u8'):
        response = StreamingHttpResponse(file_iterator(file_path))
    else:
        video_path = merge_m3u8(file_path)
        response = StreamingHttpResponse(file_iterator(video_path, True))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# 获取m3u8文件，合成视频数据流
def merge_m3u8(m3u8_file_path):
    with open(m3u8_file_path) as file:
        m3u8_content = file.read()
    file_name_header = m3u8_file_path.split('/')[-1].split('.')[0]
    ts_links = []
    # 解析m3u8文件中的子文件存放位置
    for line in m3u8_content.splitlines():
        if line.endswith('.ts'):
            ts_links.append(line)
    # 保存ts文件存放的位置 - 临时
    with open(os.path.join(settings.BASE_DIR, 'chunks', file_name_header + '_ts_list.txt'), 'w') as file:
        for ts in ts_links:
            ts_path = ts if os.path.isabs(ts) else os.path.join(os.path.dirname(m3u8_file_path), ts)
            file.write(f"file '{ts_path}'\n")

    # 使用ffmpeg 合并 TS 文件
    try:
        process = subprocess.Popen(
            ['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
             os.path.join(settings.BASE_DIR, 'chunks', file_name_header + '_ts_list.txt'), '-c', 'copy',
             os.path.join(settings.BASE_DIR, 'chunks', file_name_header + '.mp4')],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # 获取合并后的 video 数据
        video_data, error = process.communicate()
        os.remove(os.path.join(settings.BASE_DIR, 'chunks', file_name_header + '_ts_list.txt'))
        # print(process.returncode)
        if process.returncode != 0:
            return False
    except Exception as e:
        print('concat video is error :%s' % e)
        return False
    return os.path.join(settings.BASE_DIR, 'chunks', file_name_header + '.mp4')
