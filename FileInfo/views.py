import io
import json
import os
import uuid
import shutil
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from tools.logging_dec import logging_check
from .models import FileInfo
from .serializers import FileInfoSerializer
from django.utils import timezone
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
import subprocess
from PIL import Image
import threading
from utils.utils import search_file_children, sum_file_size, get_search_file_list
from django.core.files.storage import default_storage
from cryptography.fernet import Fernet
import base64
from FileShare.models import FileShare
from django.core.cache import cache
import aspose.words as aw
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from django.db.models import Q
import math
import re
import time


# 获取主页显示的数据，分页显示
@logging_check
def loadDataList(request):
    # print(timezone.now())
    if request.method != 'GET':
        return JsonResponse({
            'code': 404,
            'error': 'get dataList is wrong!'
        })
    # 当前页数
    page_now = int(request.GET.get('pageNo'))
    # 一页显示的数量
    page_size = int(request.GET.get('pageSize'))
    # 当前的分类
    category = request.GET.get('category')
    # 当前的父类id
    pid = request.GET.get('filePid', 0)
    if category == 'video':
        cate_id = 1
    elif category == 'music':
        cate_id = 2
    elif category == 'image':
        cate_id = 3
    elif category == 'doc':
        cate_id = 4
    elif category == 'others':
        cate_id = 5
    else:
        cate_id = -1
    # 获取当前发出请求的用户
    user = request.my_user
    fuzzy = request.GET.get('fileNameFuzzy', False)

    # 构造过滤条件
    filters = Q(user_id=user.user_id, del_flag=2)

    # 如果 fuzzy 存在，添加模糊查询条件
    if fuzzy:
        filters &= Q(file_name__icontains=fuzzy)

    # 如果 category != 'all'，添加分类过滤条件
    if category != 'all':
        filters &= Q(file_category=cate_id)

    if not fuzzy and category == 'all':
        filters &= Q(file_pid=pid)

    try:
        data_list = FileInfo.objects.filter(filters).order_by('-last_update_time')[
                    (page_now - 1) * page_size:page_now * page_size]
        total_num = FileInfo.objects.filter(filters).count()
    except Exception as e:
        print('filter data list is error :%s' % e)
        return JsonResponse({
            'code': 4000,
            'error': 'get datalist is wrong!'
        })
    # # 将QuerySet数据转换成json数据
    data_list = FileInfoSerializer(data_list, many=True).data

    result = {
        'code': 200,
        'data': {
            'pageTotal': math.ceil(total_num / page_size),
            'pageSize': page_size,
            'pageNo': page_now,
            'list': data_list
        }
    }
    return JsonResponse(result)


# 校验目录名是否存在
def check_file_name(name, pid, user, id):
    if id:
        return FileInfo.objects.filter(
            file_name=name,
            file_pid=pid,
            user_id=user
        ).exclude(file_id=id)
    return FileInfo.objects.filter(file_name=name, file_pid=pid, user_id=user)


# 创建目录
@logging_check
def newFoloder(request):
    if request.method == 'GET':
        return JsonResponse({
            'code': 404,
            'error': 'create new foloder is wrong'
        })
    user = request.my_user
    # print(request.body)
    data = json.loads(request.body)
    file_id = uuid.uuid4()
    # print('newfolder -- ', data)
    if check_file_name(data.get('filename'), data.get('pid'), user, None):
        return JsonResponse({
            'code': 4000,
            'error': '同级下目录名称已存在，请更改目录名称！'
        })
    FileInfo.objects.create(
        file_id=file_id,
        file_name=data.get('filename'),
        file_pid=data.get('pid'),
        user_id=user,
        folder_type=1
    )
    result = {
        'code': 200,
        'data': 'null'
    }
    return JsonResponse(result)


# 更改文件名
@logging_check
def rename(request):
    if request.method != 'POST':
        return JsonResponse({
            'code': 404,
            'error': 'rename the file is error'
        })
    body = json.loads(request.body)
    # print(body)
    if cache.get(f'file_info_${body["fileId"]}'):
        file = cache.get(f'file_info_${body["fileId"]}')
    else:
        try:
            file = FileInfo.objects.get(file_id=body['fileId'])
            cache.set(f'file_info_${body["fileId"]}', file, 60 * 60)
        except Exception as e:
            print(e)
            return JsonResponse({
                'code': 404,
                'error': 'rename the file is error'
            })

    if check_file_name(body['name'], file.file_pid, file.user_id, file.file_id):
        return JsonResponse({
            'code': 4000,
            'error': '同级下目录名称已存在，请更改目录名称！'
        })
    file.file_name = body['name']
    file.save()
    # 重命名，删除之前的缓存
    cache.set(f'file_info_${file.file_id}', file, 60 * 60)
    return JsonResponse({
        'code': 200,
        'data': 'rename the file is success'
    })


# 获得文件路径信息
# @logging_check
def get_folder_info(request):
    if request.method != 'POST':
        return JsonResponse({'code': 404, 'error': 'get file is wrong'})
    path = request.GET['path']
    file_ids = path.split('/')
    # print('---',file_ids)
    list = []
    for id in file_ids:
        if cache.get(f'file_info_${id}'):
            file = cache.get(f'file_info_${id}')
        else:
            try:
                file = FileInfo.objects.get(file_id=id)
                cache.set(f'file_info_${file.file_id}', file, 60 * 60 * 24)
            except Exception as e:
                print(e)
                return JsonResponse({'code': 404, 'error': 'get file is wrong'})
        list.append({
            'fileName': file.file_name,
            'fileId': file.file_id
        })
    return JsonResponse({
        'code': 200,
        'data': list
    })


# 获得当前pid下所有的目录
@logging_check
def get_current_list(request):
    if request.method == 'GET':
        return JsonResponse({
            'code': 404,
            'error': 'get current data list is wrong'
        })
    data = json.loads(request.body)
    user = request.my_user
    try:
        folders = FileInfo.objects.filter(
            user_id=user.user_id, file_pid=data['filePid'], del_flag=2, folder_type=1
        ).exclude(
            file_id__in=data['currentFileIds']
        )
    except Exception as e:
        print('ranme error is %s' % e)
        return JsonResponse({
            'code': 404,
            'error': 'get current data list is wrong'
        })
    data_list = FileInfoSerializer(folders, many=True).data
    return JsonResponse({
        'code': 200,
        'data': data_list
    })


# 更改目录
@logging_check
def change_file_folder(request):
    if request.method == 'GET':
        return JsonResponse({
            'code': 404,
            'data': 'move file or folder is error'
        })
    data = json.loads(request.body)

    old_pid = 0
    for file_id in data['idList']:
        if cache.get(f'file_info_${file_id}'):
            file = cache.get(f'file_info_${file_id}')
        else:
            try:
                file = FileInfo.objects.get(file_id=file_id)
            except Exception as e:
                print('move folder is error : %s' % e)
                return JsonResponse({
                    'code': 404,
                    'data': 'move file or folder is error'
                })
        if check_file_name(file.file_name, data['pid'], request.my_user, file.file_id):
            return JsonResponse({
                'code': 4000,
                'error': '改目录下有相同名称的文件/目录，请先更改名称再进行移动！'
            })
        old_pid = file.file_pid
        file.file_pid = data['pid']
        file.save()
        cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
    return JsonResponse({
        'code': 200,
        'data': 'move file is success'
    })


# 删除文件，将del_flag改为1（进入回收站）
@logging_check
def del_file(request):
    if request.method == 'GET':
        return JsonResponse({
            'code': 404,
            'error': 'del file is error'
        })
    data = json.loads(request.body)

    # 被删除的文件及其子孙目录
    file_list = []
    # 获取保存的文件目录下的所有子文件的id
    for file_id in data['idList']:
        file_list.append(search_file_children(file_id, request.my_user))
    # 删除的文件的总大小
    total_size = 0
    for file_obj in file_list:
        total_size += sum_file_size(file_obj)
    # 获得所有目录的id——list
    file_id_list = list(set(get_search_file_list(file_list)))
    # print(file_id_list)
    for file_id in file_id_list:
        if cache.get(f'file_info_${file_id}'):
            file = cache.get(f'file_info_${file_id}')
        else:
            try:
                file = FileInfo.objects.get(file_id=file_id)
            except Exception as e:
                print('del file is error: %s' % e)
                return JsonResponse({
                    'code': 404,
                    'error': 'del file is error'
                })
        file.del_flag = 1
        # 获取当前时间
        now = timezone.now()
        file.recovery_time = now
        file.save()
        cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
        # 进入回收站的同时，需要将相关联的分享删除
        file_share_list = FileShare.objects.filter(file_id=file)
        for file_share in file_share_list:
            file_share.delete()
    user = request.my_user
    user.use_space = user.use_space - total_size
    user.save()
    cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
    return JsonResponse({
        'code': 200,
        'error': 'del file is success'
    })
# 解密文件块函数
# def decrypt_data(encrypted_data):
#     # 密钥和初始化向量（IV）
#     encryption_key = b'secret-key123456'  # 确保是16字节的密钥
#     iv = b'1234567890113456'  # 确保是16字节的IV
#     # Base64 解码
#     encrypted_data_bytes = base64.b64decode(encrypted_data)
#     # 创建 AES 解密器
#     cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
#     # 解密数据并去除填充
#     decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

#     return decrypted_data

# 获得下一个文件名
def get_next_filename(file_list):
    if not file_list:
        return None
    base_name, extension = os.path.splitext(file_list[0])
    base_name = re.sub(r'\(\d+\)$', '', base_name)
    if (base_name + extension) not in file_list:
        return f'{base_name}{extension}'
    min_version = 1
    file_list.remove(f'{base_name}{extension}')
    version_list = set(re.search(r'\((\d+)\)', file).group(1)
                       for file in file_list
                       if re.search(r'\((\d+)\)', file))

    while str(min_version) in version_list:
        min_version += 1
    return f'{base_name}({min_version}){extension}'

# 文件分片上传
@logging_check
def upload_file(request):
    if request.method != 'POST':
        return JsonResponse({
            'code': 404,
            'error': 'upload file is error'
        })
    user = request.my_user
    # 获得分片
    chunk = request.FILES.get('file')
    # 当前的上传次数
    chunk_number = request.POST.get('chunkIndex')
    # 总片数
    total_chunks = request.POST.get('chunks')
    # 文件的父级id
    file_Pid = request.POST.get('filePid')
    # 文件的id
    fileId = request.POST.get('fileId')
    # 文件的md5值
    fileMd5 = request.POST.get('fileMd5')
    # 文件的真实名字
    file_name = request.POST.get('fileName')
    # w文件的总大小
    file_size = request.POST.get('fileSize')
    cache.set(f'file_uploader_${fileId}', True, 60 * 10)
    # print(file_size, user.use_space, user.total_space)
    if user.use_space + int(file_size) > user.total_space:
        return JsonResponse({
            'code': 404,
            'error': '空间不足，请删除文件或拓展空间再尝试！'
        })

    # 上传文件的状态
    status = 'uploading'
    # 分片的名字
    filename = f"{fileId}_{chunk_number}"
    try:
        fileList = FileInfo.objects.filter(file_md5=fileMd5)
    except Exception as e:
        print(e)
        return JsonResponse({
            'code': 404,
            'error': 'upload file is error'
        })
    # 获得文件的类型
    file_type = get_file_type(file_name)

    if file_type <= 3:
        file_category = file_type
    elif file_type < 9:
        file_category = 4
    else:
        file_category = 5

    # 检测文件名字是否重复
    first_name, extension_name = os.path.splitext(file_name)
    file_name_list = list(FileInfo.objects.filter(file_name__regex=rf"^{first_name}(\((\d+)\))?{extension_name}", user_id=user,file_pid=file_Pid).values())
    file_name_list = [file['file_name'] for file in file_name_list]
    temp_name = get_next_filename(file_name_list)
    if temp_name:
        file_name = temp_name
    # ---------------------------------------------
    # 如果md5存在，则有相同文件存在，不需要上传一次，直接公用一个
    if len(fileList) != 0:
        file = fileList[0]
        user.use_space = user.use_space + int(file_size)
        user.save()
        FileInfo.objects.create(
            file_id=fileId,
            file_md5=fileMd5,
            user_id=user,
            file_pid=file_Pid,
            file_size=file.file_size,
            file_name=file_name,
            file_cover=file.file_cover,
            file_path=file.file_path,
            folder_type=file.folder_type,
            file_category=file_category,
            file_type=file_type,
            status=2
        )
        return JsonResponse({
            'code': 200,
            'data': {
                'fileId': fileId,
                'status': 'upload_seconds'
            }
        })

    # -----------------------------------------
    # 保存的根本路径
    base_dir = str(settings.BASE_DIR)
    if not os.path.exists(os.path.join(base_dir, 'chunks', fileId)):
        os.mkdir(os.path.join(base_dir, 'chunks', fileId))
    path = os.path.join(base_dir, 'chunks', fileId, filename)
    # 保存分片
    # 读取上传文件的内容
    # encrypted_data = chunk.read()
    # # Base64 解码密文
    # encrypted_data = encrypted_data.decode('utf-8')
    # try:
    #     chunk_data = decrypt_data(encrypted_data)
    #     # 判断请求是否取消
    #     if not cache.get(f'file_uploader_${fileId}'):
    #         return JsonResponse({'error': '取消请求！'}, status=409)
    #     # 将解密后的数据保存为文件
    with open(path, 'wb') as f:
        f.write(chunk.read())
    # except (ValueError, KeyError) as e:
    #     print(e)
    #     return JsonResponse({'error': '非法请求！'}, status=500)

    # 当分片都上传完成，合并分片
    content_type = request.POST.get('fileType')
    if len(os.listdir(os.path.join(base_dir, 'chunks', fileId))) == int(total_chunks):
        # 所有分片上传完毕，开始合并文件
        change_file = threading.Thread(target=composite_file,
                                       args=(total_chunks, fileId, file_type, content_type, file_name, fileMd5))
        FileInfo.objects.create(
            file_id=fileId,
            file_md5=fileMd5,
            user_id=user,
            file_pid=file_Pid,
            file_size=file_size,
            file_name=file_name,
            file_cover='',
            file_path='',
            folder_type=0,
            file_category=file_category,
            file_type=file_type,
            status=0
        )
        user.use_space = user.use_space + int(file_size)
        user.save()
        cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
        change_file.start()
        status = 'upload_finish'
    return JsonResponse({
        'code': 200,
        'data': {
            'fileId': fileId,
            'status': status
        }
    })


# 取消上传 - 删除未合并的文件
@logging_check
def cancel_uploader(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'cancel the uploader is error'
        }, status=500)
    res_data = json.loads(request.body)
    file_id = res_data.get('fileId')
    cache.set(f'file_uploader_${file_id}', 0, 60 * 10)
    chunk_file_dir = os.path.join(settings.BASE_DIR, 'chunks', file_id)
    try:
        shutil.rmtree(chunk_file_dir)  # 删除目录及其中的所有内容
    except Exception as e:
        print('取消上传：' + e)
        return JsonResponse({
            'error': 'cancel the uploader is error'
        }, status=500)
    return JsonResponse({
        'code': 200,
        'status': 'success'
    })


@logging_check
def pause_uploader(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'pause the uploader is error'
        }, status=500)
    file_id = request.GET.get('file_id')
    cache.set(f'file_uploader_${file_id}', 2, 60 * 10)
    return JsonResponse({
        'code': 200,
        'status': 'success'
    })


# 获得视频的内容，进行预览
def get_video_info(request, file_id):
    # 增加缓存key
    cache_key = f'video_content_{file_id}'
    
    # 判断是获取m3u8文件还是读取具体的文件内容
    if file_id.endswith('.ts'):
        # 增加ts文件缓存
        ts_cache_key = f'ts_content_{file_id}'
        ts_content = cache.get(ts_cache_key)
        if ts_content:
            return HttpResponse(ts_content, content_type='application/octet-stream')
            
        media_dir = str(settings.MEDIA_ROOT)
        # 使用更大的buffer size提升读取效率
        with open(os.path.join(media_dir, 'file', file_id), 'rb', buffering=8192) as f:
            ts_file_content = f.read()
        
        # 缓存ts文件内容,设置较短的过期时间
        cache.set(ts_cache_key, ts_file_content, 300)  # 5分钟
        return HttpResponse(ts_file_content, content_type='application/octet-stream')

    # 检查视频内容缓存
    video_content = cache.get(cache_key)
    if video_content:
        return HttpResponse(video_content, content_type='application/octet-stream')

    # 获取视频文件信息
    if cache.get(f'file_info_${file_id}'):
        video = cache.get(f'file_info_${file_id}')
    else:
        try:
            video = FileInfo.objects.get(file_id=file_id)
            # 缓存文件信息24小时
            cache.set(f'file_info_${file_id}', video, 60 * 60 * 24)
        except Exception as e:
            print('get video is error: %s' % e)
            return JsonResponse({
                'code': 404,
                'error': 'get video is error'
            }, status=404)

    # 使用流式响应处理大文件
    def file_iterator(file_obj, chunk_size=8192):
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            yield chunk

    # 对于小文件直接返回
    if video.file_size < 10 * 1024 * 1024:  # 小于10MB
        video_content = video.file_path.read()
        cache.set(cache_key, video_content, 3600)  # 缓存1小时
        return HttpResponse(video_content, content_type='application/octet-stream')
    
    # 大文件使用流式响应
    response = StreamingHttpResponse(
        file_iterator(video.file_path),
        content_type='application/octet-stream'
    )
    response['Accept-Ranges'] = 'bytes'
    
    # 添加断点续传支持
    range_header = request.META.get('HTTP_RANGE', '').strip()
    if range_header:
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else video.file_size - 1
            if start >= 0:
                video.file_path.seek(start)
                response['Content-Range'] = f'bytes {start}-{end}/{video.file_size}'
                response.status_code = 206

    return response


# 获取文件内容
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


# 判断文件是什么类型
def get_file_type(filename):
    _, ext = os.path.splitext(filename)
    ext = ext.lower()  # 转换为小写以确保匹配
    # print('------------file type is :----',filename)
    # 根据扩展名判断文件类型
    if ext in ('.mp4', '.avi', '.mov', '.wmv', '.flv'):
        return 1
    elif ext in ('.mp3', '.wav', '.aac', '.ogg'):
        return 2
    elif ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp'):
        return 3
    elif ext == '.pdf':
        return 4
    elif ext == '.doc' or ext == '.docx':
        return 5
    elif ext == '.xls' or ext == '.xlsx':
        return 6
    elif ext == '.txt':
        return 7
    elif ext in ('.py', '.java', '.css', '.js', '.html', '.cpp', '.c', '.rb', '.sh'):
        return 8
    elif ext == '.zip':
        return 9
    else:
        return 10


# 对文件进行合成
def composite_file(total_chunks, fileId, file_type, content_type, file_name, file_md5):
    # 保存的根本路径
    base_dir = str(settings.BASE_DIR)
    # 创建一个 BytesIO 对象来存储合并后的文件内容
    merged_file = BytesIO()
    # 用来计算文件的md5值
    # md5_hash = hashlib.md5()
    for i in range(int(total_chunks)):
        chunk_path = f"{base_dir}/chunks/{fileId}/{fileId}_{i}"
        with open(chunk_path, 'rb') as chunk_file:
            chunk_file_content = chunk_file.read()
            # md5_hash.update(chunk_file_content)
            # 将分片内容写入Bytes IO对象
            merged_file.write(chunk_file_content)
        os.remove(chunk_path)  # 删除分片文件
    try:
        shutil.rmtree(f"{base_dir}/chunks/{fileId}")
    except Exception as e:
        print(e)
    merged_file.seek(0)

    if cache.get(f'file_info_${fileId}'):
        file = cache.get(f'file_info_${fileId}')
    else:
        try:
            file = FileInfo.objects.get(file_id=fileId)
        except Exception as e:
            print('get file is error: %s' % e)

    if file_type != 1:
        obj = create_others_file(file_type, fileId, file_name, merged_file, content_type)
    else:
        obj = create_video_file(merged_file, file_name, fileId)
    uploaded_file = obj['upload_file']
    cover_file = obj['cover']
    file.file_path = uploaded_file
    file.file_cover = cover_file
    file.status = 2
    file.save()
    cache.set(f'file_info_${fileId}', file, 60 * 60 * 24)
    cache.delete(f'file_user_list_${file.user_id.user_id}_${file.file_pid}')

# 对不是视频文件进行操作
def create_others_file(file_type, fileId, file_name, merged_file, content_type):
    cover_file = ''
    # 创建一个 ContentFile 对象
    content_file = ContentFile(merged_file.read())
    # 创建一个 UploadedFile 对象
    uploaded_file = UploadedFile(
        file=content_file,
        name=f"{fileId}.{file_name.split('.')[-1]}",
        content_type=content_type,  # 或者根据实际情况设置正确的 MIME 类型
        size=len(content_file),
        charset=None,
        content_type_extra=None
    )
    # print(uploaded_file)
    # 如果是图片，则生成缩略图
    if file_type == 3:
        image = Image.open(uploaded_file)
        # 创建一个 BytesIO 对象来保存缩略图的字节数据
        image_io = io.BytesIO()
        image.save(image_io, format='PNG')  # 确保使用正确的格式
        image_io.seek(0)  # 移动到 BytesIO 对象的开始位置
        thumbnail_name = '{}_.{}'.format(fileId, uploaded_file.name.split('.')[-1])
        image.thumbnail((100, 100), Image.Resampling.LANCZOS)  # 设置缩略图大小
        thumbnail_file = ContentFile(image_io.getvalue(), name=thumbnail_name)
        cover_file = thumbnail_file
    return {
        'cover': cover_file,
        'upload_file': uploaded_file
    }


# 对视频进行操作
def create_video_file(merged_file, file_name, fileId):
    # 保存的根本路径
    base_dir = str(settings.BASE_DIR)
    # 是视频文件，则合成后，对视频进行分割
    video_path = os.path.join(base_dir, 'chunks', fileId + '.' + file_name.split('.')[-1])
    # 将视频文件保存下载 - 临时
    with open(video_path, 'wb') as f:
        f.write(merged_file.read())
    cover_path = os.path.join(base_dir, 'chunks', fileId + '.jpg')
    # 对视频生成缩略图
    command = [
        '/usr/local/bin/ffmpeg', '-i',
        video_path, '-ss',
        '00:00:01', '-vframes',
        '1', cover_path
    ]
    subprocess.run(command, check=True)
    # 读取缩略图文件内容
    with open(cover_path, 'rb') as thumb_file:
        cover_content = thumb_file.read()

    # 删除原来的缩略图
    os.remove(cover_path)
    # 创建 ContentFile 对象
    cover_file = ContentFile(cover_content, name=fileId + '.jpg')

    # 对视频进行分割
    m3u8_path = os.path.join(base_dir, 'media', 'file', fileId + '.m3u8')
    # 构建 FFmpeg 命令
    command = (
        '/usr/local/bin/ffmpeg -i {} -c:v libx264 -c:a aac -strict -2 '
        '-f hls -hls_time 300 -hls_list_size 0 {}'
    ).format(video_path, m3u8_path)
    # 执行命令
    subprocess.call(command, shell=True)
    # print(m3u8_path)
    # 读取 M3U8 文件内容
    with open(m3u8_path, 'rb') as m3u8_file:
        m3u8_content = m3u8_file.read()
    # 创建 ContentFile 对象
    m3u8_content_file = ContentFile(m3u8_content, name=fileId + '.m3u8')
    uploaded_file = m3u8_content_file
    # 删除原来生成的m3u8文件
    os.remove(m3u8_path)
    # 删除合成的视频
    os.remove(video_path)
    return {
        'cover': cover_file,
        'upload_file': uploaded_file
    }


# 实现文件下载功能 - 获得文件下载链接
@logging_check
def create_download_url(request, file_id):
    cipher_suite = Fernet(settings.FERNET_KEY)

    if request.method != 'GET':
        return JsonResponse({
            'error': 'create file download url is error'
        }, status=404)

    if cache.get(f'file_info_${file_id}'):
        file = cache.get(f'file_info_${file_id}')
    else:
        try:
            file = FileInfo.objects.get(file_id=file_id)
        except Exception as e:
            print(e)
            return JsonResponse({
                'error': 'create file download url is error'
            })
    file_path = file.file_path
    file_url = default_storage.url(file_path).encode('utf-8')
    data = base64.b64encode(cipher_suite.encrypt(file_url)).decode('utf-8')
    return JsonResponse({
        'data': data,
        'status': 'success',
        'fileName': file.file_name,
        'code': 200
    })


def download(request, url_base64, filename):
    # 增加下载缓存key
    cache_key = f'download_{url_base64}'

    if request.method != 'GET':
        return JsonResponse({
            'error': 'download file is error'
        }, status=404)

    try:
        # 解密文件路径
        cipher_suite = Fernet(settings.FERNET_KEY)
        url_data = base64.b64decode(url_base64.encode('utf-8'))
        file_url = cipher_suite.decrypt(url_data).decode('utf-8')
        file_path = str(settings.BASE_DIR) + file_url

        if not os.path.exists(file_path):
            return JsonResponse({
                'error': 'File not found'
            }, status=404)

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 优化分块读取文件
        def file_iterator(filepath, chunk_size=8192):
            try:
                with open(filepath, 'rb', buffering=chunk_size) as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                print(f'Error reading file: {e}')
                raise

        # 创建流式响应
        response = StreamingHttpResponse(
            file_iterator(file_path),
            content_type='application/octet-stream'
        )

        # 添加断点续传支持
        range_header = request.META.get('HTTP_RANGE', '').strip()
        if range_header:
            range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                if start >= 0:
                    # 打开文件并移动到指定位置
                    def range_iterator(start, end, chunk_size=8192):
                        with open(file_path, 'rb') as f:
                            f.seek(start)
                            remaining = end - start + 1
                            while remaining > 0:
                                chunk_size = min(chunk_size, remaining)
                                data = f.read(chunk_size)
                                if not data:
                                    break
                                remaining -= len(data)
                                yield data

                    response = StreamingHttpResponse(
                        range_iterator(start, end),
                        status=206,
                        content_type='application/octet-stream'
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                    response['Content-Length'] = end - start + 1

        # 设置响应头
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        if not range_header:
            response['Content-Length'] = file_size

        # 处理m3u8文件
        if file_path.endswith('.m3u8'):
            video_path = merge_m3u8(file_path)
            if video_path:
                response = StreamingHttpResponse(
                    file_iterator(video_path),
                    content_type='application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Content-Length'] = os.path.getsize(video_path)
                
                # 使用线程异步删除临时文件
                def delete_temp_file():
                    try:
                        time.sleep(1)  # 等待传输完成
                        os.remove(video_path)
                    except Exception as e:
                        print(f'Error deleting temp file: {e}')
                
                threading.Thread(target=delete_temp_file).start()
            else:
                return JsonResponse({'error': 'Failed to process video file'}, status=500)

        return response

    except Exception as e:
        print(f'Download error: {e}')
        return JsonResponse({
            'error': 'Download failed',
            'detail': str(e)
        }, status=500)


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
