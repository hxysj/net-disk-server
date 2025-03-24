from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from FileShare.models import FileShare
from tools.logging_dec import code_check, logging_check
from FileInfo.models import FileInfo
from .serializers import webShareSerializer
from django.conf import settings
import jwt
import time
import json
from FileInfo.serializers import FileInfoSerializer
from utils.utils import copy_file, check_file_id, sum_file_size, search_file_children
import os
import base64
from cryptography.fernet import Fernet
from django.core.files.storage import default_storage
import subprocess
from django.utils import timezone
from django.core.cache import cache
import math
import re
from io import BytesIO
import aspose.words as aw
import time

# 获得分享信息
def get_share_file(request, share_id):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'get share file is error'
        }, status=404)
    # 如果有缓存，就走缓存
    if cache.get(f'share_file_${share_id}'):
        share_file_data = cache.get(f'share_file_${share_id}')
    else:
        try:
            share_file = FileShare.objects.get(share_id=share_id)
        except Exception as e:
            print('get share file is error: %s' % e)
            return JsonResponse({
                'error': 'get share file is error'
            }, status=404)
        now_time = timezone.now()
        if now_time > share_file.expire_time:
            share_file.delete()
            return JsonResponse({
                'error': 'get share file is error'
            }, status=404)
        # 设置分享链接信息的失效时间
        expire_time = (share_file.expire_time - now_time).total_seconds()
        share_file_data = webShareSerializer(share_file).data
        cache.set(f'share_file_${share_id}', share_file_data, expire_time)
    return JsonResponse(share_file_data)


# 校验提取码 - 顺便将浏览次数 + 1
def check_code(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'check code is error'
        }, status=404)
    # print(request.GET)
    share_id = request.GET['shareId']
    code = request.GET['code']
    if cache.get(f'share_file_info_${share_id}'):
        # print('走缓存')
        share_file = cache.get(f'share_file_info_${share_id}')
        if share_file.code != code:
            return JsonResponse({
                'error': 'check code is error'
            }, status=403)
        share_file.viewed()
    else:
        try:
            share_file = FileShare.objects.get(share_id=share_id, code=code)
            now_time = timezone.now()
            # 设置分享链接信息的失效时间
            expire_time = (share_file.expire_time - now_time).total_seconds()
            cache.set(f'share_file_info_${share_id}', share_file, expire_time)
            share_file.viewed()
        except Exception as e:
            print('check share code is error: %s' % e)
            return JsonResponse({
                'error': 'check code is error'
            }, status=403)
    code_token = make_token(code, share_id)
    # print('--->make-token-code is : %s' % code_token)
    response = JsonResponse({'code': 200, 'code_check': code_token})
    response.set_cookie('check_token', code_token, expires=time.time() + (60 * 10))
    return response


# 生成token
def make_token(code, share_id, expire=60 * 10):
    key = settings.CODE_TOKEN_KEY
    now_time = time.time()
    payload_data = {
        'code': code,
        'shareId': share_id,
        'exp': now_time + expire
    }
    # print(payload_data)
    return jwt.encode(payload_data, key, algorithm='HS256')


# 获得分享的文件信息
@code_check
def load_file_list(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'get share file list is error'
        }, status=404)
    # 获得请求中的code
    code = request.share_code
    share_id = request.GET.get('shareId')
    share_file = FileShare.objects.get(code=code, share_id=share_id)
    file = share_file.file_id
    share_user = share_file.user_id
    pid = request.GET.get('pid')
    page_now = int(request.GET.get('pageNo'))
    page_size = int(request.GET.get('pageSize'))
    total_count = 0
    try:
        # 如果pid等于文件的父级id，证明链接要访问的正是读取文件，返回文件信息
        if pid == file.file_pid:
            file_list = [file]
        else:
            if check_file_id(file.file_id, pid, share_user):
                file_list = FileInfo.objects.filter(file_pid=pid, del_flag=2, user_id=share_user).order_by(
                    '-create_time')[(page_now - 1) * page_size:page_now * page_size]
                # 获取总的记录数（用于计算页数）
                total_count = FileInfo.objects.filter(file_pid=pid, del_flag=2, user_id=share_user).count()
            else:
                return JsonResponse({
                    'error': 'get share file list is error'
                }, status=4000)
    except Exception as e:
        print(e)
        return JsonResponse({
            'error': 'get share file list is error'
        }, status=4000)
    data = FileInfoSerializer(file_list, many=True).data
    return JsonResponse({
        'pageNo': page_now,
        'pageSize': page_size,
        'list': data,
        'pageTotal': math.ceil(total_count / page_size)
    })


# 获得文件的内容信息
# @code_check
def get_file(request, file_id):
    # 增加文件内容缓存key
    cache_key = f'file_content_{file_id}'
    
    # 检查文件内容缓存
    file_content = cache.get(cache_key)
    if file_content:
        return HttpResponse(file_content, content_type='application/octet-stream')

    # 获取文件信息
    if cache.get(f'file_info_${file_id}'):
        file = cache.get(f'file_info_${file_id}')
    else:
        try:
            file = FileInfo.objects.get(file_id=file_id)
            cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
        except Exception as e:
            print('get file is error: %s' % e)
            return JsonResponse({
                'data': 'get file is error'
            }, status=500)

    # 使用流式响应处理大文件
    def file_iterator(file_obj, chunk_size=8192):
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            yield chunk

    # 处理不同类型的文件
    if file.file_type == 5:  # doc/docx文件
        try:
            # 使用缓存存储转换后的docx文件
            docx_cache_key = f'docx_content_{file_id}'
            docx_content = cache.get(docx_cache_key)
            if docx_content:
                return HttpResponse(docx_content, content_type='application/octet-stream')

            # 转换doc文件
            file_stream = BytesIO(file.file_path.read())
            doc = aw.Document(file_stream)
            docx_blob_stream = BytesIO()
            doc.save(docx_blob_stream, aw.SaveFormat.DOCX)
            docx_blob_stream.seek(0)
            file_content = docx_blob_stream.getvalue()
            
            # 缓存转换后的文件内容
            cache.set(docx_cache_key, file_content, 60 * 60)  # 1小时
            return HttpResponse(file_content, content_type='application/octet-stream')
        except Exception as e:
            print('convert doc file error:', e)
            # 转换失败时返回原始文件
            file_content = file.file_path.read()
            return HttpResponse(file_content, content_type='application/octet-stream')
    
    # 对于小文件直接返回并缓存
    if file.file_size < 10 * 1024 * 1024:  # 小于10MB
        file_content = file.file_path.read()
        cache.set(cache_key, file_content, 3600)  # 缓存1小时
        return HttpResponse(file_content, content_type='application/octet-stream')
    
    # 大文件使用流式响应
    response = StreamingHttpResponse(
        file_iterator(file.file_path),
        content_type='application/octet-stream'
    )
    response['Accept-Ranges'] = 'bytes'
    
    # 添加断点续传支持
    range_header = request.META.get('HTTP_RANGE', '').strip()
    if range_header:
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file.file_size - 1
            if start >= 0:
                file.file_path.seek(start)
                response['Content-Range'] = f'bytes {start}-{end}/{file.file_size}'
                response.status_code = 206

    # 添加文件下载相关头信息
    response['Content-Disposition'] = f'attachment; filename="{file.file_name}"'
    response['Content-Length'] = file.file_size
    
    return response


# 获得视频的内容，进行预览
# @code_check
def get_video_info(request, file_id):
    # 判断是获取m3u8文件还是读取具体的文件内容
    if file_id.endswith('.ts'):
        # print(file_id)
        media_dir = str(settings.MEDIA_ROOT)
        with open(os.path.join(media_dir, 'file', file_id), 'rb') as f:
            ts_file_content = f.read()
        return HttpResponse(ts_file_content, content_type='application/octet-stream')
    # 判断缓存中是否存在视频的信息
    if cache.get(f'file_info_{file_id}'):
        video = cache.get(f'file_info_{file_id}')
    else:
        try:
            video = FileInfo.objects.get(file_id=file_id)
            cache.set(f'file_info_{file_id}', video, 60 * 60 * 24)
        except Exception as e:
            print('get video is error: %s' % e)
            return JsonResponse({
                'code': 404,
                'error': 'get video is error'
            }, status=404)
    # print(video)
    video_file = video.file_path.read()
    # print(type(video_file))
    return HttpResponse(video_file, content_type='application/octet-stream')


# 保存到我的网盘
@logging_check
@code_check
def save_share(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'save share file is error'
        }, status=403)
    # print(search_file_children)
    body = json.loads(request.body)
    # 要保存的文件列表
    file_id_list = body.get('shareFileIds')
    # 要保存的位置
    save_folder_id = body.get('myFolderId')
    # 分享的id
    share_id = request.GET.get('shareId')
    if cache.get(f'share_file_info_${share_id}'):
        share_file = cache.get(f'share_file_info_${share_id}')
    else:
        share_file = FileShare.objects.get(share_id=share_id, code=request.share_code)
        now_time = timezone.now()
        # 设置分享链接信息的失效时间
        expire_time = (share_file.expire_time - now_time).total_seconds()
        cache.set(f'share_file_info_{share_id}', share_file, expire_time)
    file_list = []
    # 获取保存的文件目录下的所有子文件的id
    for file_id in file_id_list:
        file_list.append(search_file_children(file_id, share_file.user_id))

    # 获取当前登录的用户
    user = request.my_user
    # 文件总大小
    total_size = 0
    for file_obj in file_list:
        total_size += sum_file_size(file_obj)
    # print(total_size)
    if user.total_space - user.use_space < total_size:
        return JsonResponse({
            'status': 'error',
            'code': 403,
            'message': '空间不足，请删除没有用到的文件或拓展空间吧！'
        })

    for file_obj in file_list:
        copy_file(file_obj, user, save_folder_id)
    user.use_space = user.use_space + total_size
    user.save()
    cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
    return JsonResponse({
        'status': 'success',
        'code': 200,
        'message': '保存成功'
    })


# 检查是否登录
@logging_check
def check_login(request):
    return JsonResponse({
        'code': 'success'
    })


# 实现文件下载功能 - 获得文件下载链接
@code_check
def create_download_url(request, file_id):
    cipher_suite = Fernet(settings.FERNET_KEY)

    if request.method != 'GET':
        return JsonResponse({
            'error': 'create file download url is error'
        }, status=404)
    if cache.get(f'file_info_{file_id}'):
        file = cache.get(f'file_info_{file_id}')
    else:
        try:
            file = FileInfo.objects.get(file_id=file_id)
            cache.set(f'file_info_{file_id}', file, 60 * 60 * 24)
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
