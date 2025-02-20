import json
import os.path
from FileInfo.models import FileInfo
from tools.logging_dec import logging_check
from django.http import JsonResponse
from .serializers import recycleSerializer
from utils.utils import search_file_children, sum_file_size, get_search_file_list
from django.conf import settings
from django.core.cache import cache
import math


@logging_check
def load_recycle_list(request):
    user = request.my_user
    # 获取页码数
    page_now = int(request.GET.get('pageNo'))
    # 获得页数
    page_size = int(request.GET.get('pageSize'))
    try:
        files = FileInfo.objects.filter(user_id=user, del_flag=1).order_by('-recovery_time')[
                (page_now - 1) * page_size:page_now * page_size]
        total_num = FileInfo.objects.filter(user_id=user, del_flag=1).count()
    except Exception as e:
        print('get recycle is error: %s' % e)
        return JsonResponse({
            'error': 'get recycle is error!'
        }, status=404)
    # 将QuerySet数据转换成json数据
    data_list = recycleSerializer(files, many=True).data
    return JsonResponse({
        'pageSize': page_size,
        'pageTotal': math.ceil(total_num / page_size),
        'pageNo': page_now,
        'list': data_list
    })


# 还原文件
@logging_check
def recover_file(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'recover file the method is error'
        }, status=500)
    user = request.my_user
    data = json.loads(request.body)
    file_list = []
    # 获取保存的文件目录下的所有子文件的id
    # for file_id in data['fileIds']:
    #     file_list.append(search_file_children(file_id, request.my_user))
    # # 删除的文件的总大小
    # total_size = 0
    # for file_obj in file_list:
    #     total_size += sum_file_size(file_obj)
    # 获得所有目录的id——list
    # file_id_list = list(set(get_search_file_list(file_list)))
    total_size = 0
    for file_id in data['fileIds']:
        if cache.get(f'file_info_${file_id}'):
            file = cache.get(f'file_info_${file_id}')
        else:
            file = FileInfo.objects.get(file_id=file_id)
        if file.file_size:
            total_size += file.file_size
    if user.use_space + total_size > user.total_space:
        return JsonResponse({
            'error': '空间不足，请拓展空间或删除其他文件再继续!'
        }, status=403)
    for file_id in data['fileIds']:
        if cache.get(f'file_info_${file_id}'):
            file = cache.get(f'file_info_${file_id}')
        else:
            try:
                file = FileInfo.objects.get(file_id=file_id)
            except Exception as e:
                print('recover file is error: %s' % e)
                return JsonResponse({
                    'error': '获取文件错误！'
                }, status=404)
        file.del_flag = 2
        file.file_pid = 0
        file.save()
        cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
    user.use_space = user.use_space + total_size
    user.save()
    cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
    return JsonResponse({
        'status': 'success',
        'msg': '还原成功！'
    })


# 彻底删除
@logging_check
def delete_file(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'delete file the method is error'
        }, status=500)
    data = json.loads(request.body)
    # file_list = []
    # 获取保存的文件目录下的所有子文件的id
    # for file_id in data['fileIds']:
    #     file_list.append(search_file_children(file_id, request.my_user))

    # 获得所有目录的id——list
    # file_id_list = list(set(get_search_file_list(file_list)))
    # print(file_id_list)
    for file_id in data['fileIds']:
        if cache.get(f'file_info_${file_id}'):
            file = cache.get(f'file_info_${file_id}')
        else:
            try:
                file = FileInfo.objects.get(file_id=file_id)
            except Exception as e:
                print('recover file is error: %s' % e)
                return JsonResponse({
                    'error': '获取文件错误！'
                }, status=404)
        # 如果是目录
        if file.folder_type == 1:
            file.delete()
            cache.delete(f'file_info_${file_id}')
            continue
        file_md5 = file.file_md5
        same_md5_file = FileInfo.objects.filter(file_md5=file_md5)
        # print(same_md5_file)
        if len(same_md5_file) == 1:
            file_path = file.file_path.name
            # print(file.file_path.name)
            os.remove(os.path.join(settings.MEDIA_ROOT, file_path))
            # 如果是视频文件，则需要将ts文件删除
            if file.file_type == 1:
                ts_file_header = file_path.split('/')[1].split('.')[0]
                for file_item in os.listdir(os.path.join(settings.MEDIA_ROOT, 'file')):
                    if file_item.startswith(ts_file_header):
                        os.remove(os.path.join(settings.MEDIA_ROOT, 'file', file_item))
            # 如果是图片和视频则将封面删除
            if file.file_type == 1 or file.file_type == 3:
                cover_file_header = file_path.split('/')[1].split('.')[0]
                for file_item in os.listdir(os.path.join(settings.MEDIA_ROOT, 'cover')):
                    if file_item.startswith(cover_file_header):
                        os.remove(os.path.join(settings.MEDIA_ROOT, 'cover', file_item))
            # print(file_path)
        file.delete()
        if cache.get(f'file_info_${file_id}'):
            cache.delete(f'file_info_${file_id}')
    return JsonResponse({
        'status': 'success',
        'msg': '删除成功！'
    })
