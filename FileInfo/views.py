import io
import json
import os
import uuid
import hashlib
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from tools.logging_dec import logging_check
from .models import FileInfo
from django.core.paginator import Paginator
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
    pageNow = request.GET.get('pageNo')
    # 一页显示的数量
    pageSize = request.GET.get('pageSize')
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
    # 获取当前发出请求的用户
    user = request.my_user
    fuzzy =  request.GET.get('fileNameFuzzy', False)
    if cache.get(f'file_user_list_${user.user_id}_${pid}'):
        # print('读取缓存')
        datalist = cache.get(f'file_user_list_${user.user_id}_${pid}')
    else:
        # print('无缓存')
        try:
            datalist = FileInfo.objects.filter(user_id=user.user_id, file_pid=pid).order_by('-last_update_time')
            cache.set(f'file_user_list_${user.user_id}_${pid}', datalist, 60 * 60)
        except Exception as e:
            print('filter data list is error : %s' % e)
            return JsonResponse({
                'code': 404,
                'error': 'get dataList is wrong!'
            })
    # print(datalist)
    # 获得没有删除的文件
    datalist = [file for file in datalist if file.del_flag == 2]
    # 如果有搜索
    if fuzzy:
        datalist = [file for file in datalist if fuzzy in file.file_name]
    # 如果是分类
    if category != 'all':
        datalist = [file for file in datalist if file.file_category == cate_id]
    # 对数据进行分类
    paginator = Paginator(datalist, pageSize)
    data = paginator.page(pageNow)
    # 将QuerySet数据转换成json数据
    datalist = FileInfoSerializer(data, many=True).data
    # datalist = [ob['fields'] for ob in json.loads(serializers.serialize('json', data))]
    # print(datalist)
    result = {
        'code': 200,
        'data': {
            'pageTotal': paginator.num_pages,
            'pageSize': pageSize,
            'pageNo': pageNow,
            'list': datalist
        }
    }
    return JsonResponse(result)


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
    FileInfo.objects.create(
        file_id=file_id,
        file_name=data.get('filename'),
        file_pid=data.get('pid'),
        user_id=user,
        folder_type=1
    )
    # 新目录创建，删除之前的缓存
    if cache.get(f'file_user_list_${user.user_id}_${data.get("pid")}'):
        cache.delete(f'file_user_list_${user.user_id}_${data.get("pid")}')
    if cache.get(f'admin_file_list_${data.get("pid")}'):
        cache.delete(f'admin_file_list_${data.get("pid")}')
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
    file.file_name = body['name']
    file.save()
    # 重命名，删除之前的缓存
    if cache.get(f'file_user_list_${request.my_user.user_id}_${file.file_pid}'):
        # print('删除之前缓存')
        cache.delete(f'file_user_list_${request.my_user.user_id}_${file.file_pid}')
    cache.set(f'file_info_${file.file_id}', file, 60 * 60)
    if cache.get(f'admin_file_list_${file.file_pid}'):
        cache.delete(f'admin_file_list_${file.file_pid}')
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
    if cache.get(f'file_user_list_${user.user_id}_${data["filePid"]}'):
        file_list = cache.get(f'file_user_list_${user.user_id}_${data["filePid"]}')
        folders = [file for file in file_list if file.folder_type == 1 and file.file_id not in data['currentFileIds']]
    else:
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
    # print(data)
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
        old_pid = file.file_pid
        file.file_pid = data['pid']
        file.save()
        cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
    if cache.get(f'file_user_list_${request.my_user.user_id}_${data["pid"]}'):
        cache.delete(f'file_user_list_${request.my_user.user_id}_${data["pid"]}')
    if cache.get(f'file_user_list_${request.my_user.user_id}_${old_pid}'):
        cache.delete(f'file_user_list_${request.my_user.user_id}_${old_pid}')
    cache.delete(f'user_share_${request.my_user.user_id}')
    cache.delete(f'admin_file_list_${old_pid}')
    cache.delete(f'admin_file_list_${data["pid"]}')
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
        cache.delete(f'file_user_list_${request.my_user.user_id}_${file.file_pid}')
        cache.delete(f'admin_file_list_${file.file_pid}')
        # 进入回收站的同时，需要将相关联的分享删除
        file_share_list = FileShare.objects.filter(file_id=file)
        for file_share in file_share_list:
            file_share.delete()
    user = request.my_user
    user.use_space = user.use_space - total_size
    user.save()
    cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
    cache.delete(f'user_share_${user.user_id}')
    cache.delete(f'user_list')
    return JsonResponse({
        'code': 200,
        'error': 'del file is success'
    })


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
    print(file_size, user.use_space, user.total_space)
    if user.use_space + int(file_size) > user.total_space:
        return JsonResponse({
            'code': 404,
            'error': '空间不足，请删除文件或拓展空间再尝试！'
        })

    # 上传文件的状态
    status = 'uploading'
    # 分片的名字
    filename = f"{fileId}_{chunk_number}"
    # print('-----> filename ----',filename)
    try:
        fileList = FileInfo.objects.filter(file_md5=fileMd5)
    except Exception as e:
        print(e)
        return JsonResponse({
            'code': 404,
            'error': 'upload file is error'
        })
    content_type = chunk.content_type
    # 获得文件的类型
    file_type = get_file_type(file_name)

    if file_type <= 3:
        file_category = file_type
    elif file_type < 9:
        file_category = 4
    else:
        file_category = 5
    # ---------------------------------------------
    # 如果md5存在，则有相同文件存在，不需要上传一次，直接公用一个
    # print('----->',fileList)
    # print('------->chunk number --->',chunk_number,total_chunks)
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
        # print('12323-存在了')
        cache.delete(f'file_user_list_${user.user_id}_${file_Pid}')
        cache.delete(f'admin_file_list_${file_Pid}')
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
    path = os.path.join(base_dir, 'chunks', filename)
    # 保存分片
    # print(file_name)
    with open(path, 'wb') as f:
        for chunk in chunk.chunks():
            f.write(chunk)
    # 当分片都上传完成，合并分片
    if int(chunk_number) + 1 == int(total_chunks):
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
        cache.delete(f'file_user_list_${user.user_id}_${file_Pid}')
        cache.delete(f'admin_file_list_${file_Pid}')
        user.use_space = user.use_space + int(file_size)
        user.save()
        cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
        cache.delete(f'user_list')
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
    chunk_files = os.listdir(os.path.join(settings.BASE_DIR, 'chunks'))
    # print(chunk_files)
    for file_name in chunk_files:
        if file_name.startswith(file_id):
            try:
                os.remove(os.path.join(settings.BASE_DIR, 'chunks', file_name))
            except Exception as e:
                print(e)
                return JsonResponse({
                    'error': 'cancel the uploader is error'
                }, status=500)
    return JsonResponse({
        'code': 200,
        'status': 'success'
    })


# 获得视频的内容，进行预览
def get_video_info(request, file_id):
    # 判断是获取m3u8文件还是读取具体的文件内容
    if file_id.endswith('.ts'):
        # print(file_id)
        media_dir = str(settings.MEDIA_ROOT)
        with open(os.path.join(media_dir, 'file', file_id), 'rb') as f:
            ts_file_content = f.read()
        return HttpResponse(ts_file_content, content_type='application/octet-stream')
    if cache.get(f'file_info_${file_id}'):
        video = cache.get(f'file_info_${file_id}')
    else:
        try:
            video = FileInfo.objects.get(file_id=file_id)
            cache.set(f'file_info_${file_id}', video, 60 * 60 * 24)
        except Exception as e:
            print('get video is error: %s' % e)
            return JsonResponse({
                'code': 404,
                'error': 'get video is error'
            }, status=404)
    video_file = video.file_path.read()
    # print(video_file)
    return HttpResponse(video_file, content_type='application/octet-stream')


# 获取文件内容
def get_file(request, file_id):
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
    if file.file_type == 5:
        # 判断文件为doc、docx文件，讲doc文件的文件流转换成docx的文件流
        # 使用aspose-words进行转换会有水印
        file_stream = BytesIO(file.file_path.read())
        doc = aw.Document(file_stream)
        docx_blob_stream = BytesIO()
        doc.save(docx_blob_stream, aw.SaveFormat.DOCX)
        docx_blob_stream.seek(0)
        file_content = docx_blob_stream.getvalue()
    else:
        file_content = file.file_path.read()
    return HttpResponse(file_content, content_type='application/octet-stream')


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
    for i in range(int(total_chunks)):
        chunk_path = f"{base_dir}/chunks/{fileId}_{i}"
        with open(chunk_path, 'rb') as chunk_file:
            # 将分片内容写入Bytes IO对象
            merged_file.write(chunk_file.read())
        os.remove(chunk_path)  # 删除分片文件
    merged_file.seek(0)

    if cache.get(f'file_info_${fileId}'):
        file = cache.get(f'file_info_${fileId}')
    else:
        try:
            file = FileInfo.objects.get(file_id=fileId)
        except Exception as e:
            print('get file is error: %s' % e)
    # 计算出来的md5值不同
    # 合成成功后计算文件的md5值
    # md5_hash = hashlib.md5()
    # chunk_size = 1024 * 1024
    # i = 0
    # while True:
    #     data = merged_file.read(chunk_size)
    #     if not data:
    #         break
    #     md5_hash.update(data)
    # file_md5_compile = md5_hash.hexdigest()
    # # 判断合成后的文件的md5值和上传的文件的md5值是否相同，如果不同则文件传输出现错误，转码失败
    # print(file_md5, file_md5_compile)
    # 计算完成后将file的指针重新设置为0
    # merged_file.seek(0)
    if file_type != 1:
        obj = create_others_file(file_type, fileId, file_name, merged_file, content_type)
    else:
        obj = create_video_file(merged_file, file_name, fileId)
    uploaded_file = obj['upload_file']
    cover_file = obj['cover']
    # print('-------->>>>>',obj)

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
    # print(file_name, fileId)
    # 保存的根本路径
    base_dir = str(settings.BASE_DIR)
    # 是视频文件，则合成后，对视频进行分割
    # print(file_name)
    video_path = os.path.join(base_dir, 'chunks', fileId + '.' + file_name.split('.')[-1])
    # 将视频文件保存下载 - 临时
    with open(video_path, 'wb') as f:
        # 将 BytesIO 对象的内容写入文件
        f.write(merged_file.read())
    cover_path = os.path.join(base_dir, 'chunks', fileId + '.jpg')
    # 对视频生成缩略图
    command = [
        'ffmpeg', '-i',
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
        'ffmpeg -i {} -c:v libx264 -c:a aac -strict -2 '
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
        print(filepath)
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
        # os.remove(video_path)
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
