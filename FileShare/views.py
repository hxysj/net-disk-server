from tools.logging_dec import logging_check
from django.http import JsonResponse
from .models import FileShare
from FileInfo.models import FileInfo
from django.core.paginator import Paginator
from .serializers import shareSerializer
import random
import string
import uuid
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from django.utils import timezone
from django.core.cache import cache


# 获取分享文件的列表
@logging_check
def load_share_file(request):
    if request.method != 'GET':
        return JsonResponse({
            'code': 400,
            'error': 'get share file list is error'
        }, status=404)
    user = request.my_user
    if cache.get(f'user_share_${user.user_id}'):
        file_list = cache.get(f'user_share_${user.user_id}')
    else:
        try:
            file_list = FileShare.objects.filter(user_id=user).order_by('-share_time')
            cache.set(f'user_share_${user.user_id}', file_list, 60 * 60)
        except Exception as e:
            print('get share file list is error : %s' % e)
            return JsonResponse({
                'code': 400,
                'error': 'get share file list is error'
            }, status=404)
    now_time = timezone.now()
    file_list_result = []
    expire_list = []
    for file in file_list:
        if file.expire_time <= now_time:
            expire_list.append(file)
            continue
        file_list_result.append(file)
    if len(expire_list):
        cache.delete(f'user_share_${user.user_id}')
    for file in expire_list:
        file.delete()
    # 当前页码数
    pageNow = int(request.GET.get('pageNo'))
    # 一页显示的数量
    pageSize = int(request.GET.get('pageSize'))
    pagination = Paginator(file_list_result, pageSize)
    dataList = pagination.page(pageNow)
    dataList = shareSerializer(dataList, many=True).data
    return JsonResponse({
        'pageNo': pageNow,
        'pageSize': pageSize,
        'pageTotal': pagination.num_pages,
        'list': dataList
    })


# 分享文件
@logging_check
def share_file(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'share file is error'
        }, status=404)
    # 分享的文件id
    file_id = request.GET.get('fileId')
    file = FileInfo.objects.get(file_id=file_id)
    # 获得当前时间
    now = datetime.now()
    # 分享的天数  0（1天），1（7天），2（30天），3（永久有效）
    valid_type = int(request.GET.get('validType'))
    if valid_type == 0:
        valid_time_later = now + timedelta(days=1)
    elif valid_type == 1:
        valid_time_later = now + timedelta(days=7)
    elif valid_type == 2:
        valid_time_later = now + timedelta(days=30)
    elif valid_type == 3:
        valid_time_later = now + relativedelta(years=999)

    expire_time = valid_time_later.strftime('%Y-%m-%d %H:%M:%S')

    # 提取码
    code = request.GET.get('code', random_code())
    # print(code, file_id, type(valid_type))
    share_id = uuid.uuid4()
    user = request.my_user

    try:
        FileShare.objects.create(user_id=user,
                                 file_id=file,
                                 share_id=share_id,
                                 valid_type=valid_type,
                                 expire_time=expire_time,
                                 code=code
                                 )
    except Exception as e:
        print('create share file is error :%s' % e)
        return JsonResponse({
            'error': 'share file is error'
        }, status=404)
    if cache.get(f'user_share_${user.user_id}'):
        cache.delete(f'user_share_${user.user_id}')
    return JsonResponse({
        'code': code,
        'shareId': share_id
    })


# 取消分享
@logging_check
def cancel_share(request):
    if request.method != 'POST':
        return JsonResponse({
            'code': 404,
            'error': 'cancel share file is error '
        })
    data = json.loads(request.body)
    shareIds = data.get('shareIds')
    for id in shareIds:
        if cache.get(f'file_share_info_${id}'):
            file = cache.get(f'file_share_info_${id}')
        else:
            try:
                file = FileShare.objects.get(share_id=id)
            except Exception as e:
                print('get share file is error %s' % e)
                return JsonResponse({
                    'code': 404,
                    'error': 'cancel share file is error '
                })
        file.delete()
        cache.delete(f'share_file_${id}')
        cache.delete(f'share_file_info_${id}')
    if cache.get(f'user_share_${request.my_user.user_id}'):
        cache.delete(f'user_share_${request.my_user.user_id}')
    return JsonResponse({
        'code': 200,
        'status': 'success',
        'data': '取消分享成功！'
    })


# 生成随机提取码
def random_code():
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return random_string
