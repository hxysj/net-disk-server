from tools.logging_dec import logging_check
from django.http import JsonResponse
from .models import FileShare
from FileInfo.models import FileInfo
from .serializers import shareSerializer
import random
import string
import uuid
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from django.utils import timezone
from django.core.cache import cache
import math


# 获取分享文件的列表
@logging_check
def load_share_file(request):
    if request.method != 'GET':
        return JsonResponse({
            'code': 400,
            'error': 'get share file list is error'
        }, status=404)
    user = request.my_user

    now_time = timezone.now()
    # 当前页码数
    page_now = int(request.GET.get('pageNo'))
    # 一页显示的数量
    page_size = int(request.GET.get('pageSize'))

    try:
        file_list = FileShare.objects.filter(user_id=user, expire_time__gt=now_time).order_by('-share_time')[
                    (page_now - 1) * page_size:page_now * page_size]
        total_num = FileShare.objects.filter(user_id=user, expire_time__gt=now_time).count()
    except Exception as e:
        print('get share file list is error : %s' % e)
        return JsonResponse({
            'code': 400,
            'error': 'get share file list is error'
        }, status=404)
    data_list = shareSerializer(file_list, many=True).data
    return JsonResponse({
        'pageNo': page_now,
        'pageSize': page_size,
        'pageTotal': math.ceil(total_num / page_size),
        'list': data_list
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
    else:
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
    share_ids = data.get('shareIds')
    for s_id in share_ids:
        if cache.get(f'file_share_info_${s_id}'):
            file = cache.get(f'file_share_info_${s_id}')
        else:
            try:
                file = FileShare.objects.get(share_id=s_id)
            except Exception as e:
                print('get share file is error %s' % e)
                return JsonResponse({
                    'code': 404,
                    'error': 'cancel share file is error '
                })
        file.delete()
        cache.delete(f'share_file_${s_id}')
        cache.delete(f'share_file_info_${s_id}')

    return JsonResponse({
        'code': 200,
        'status': 'success',
        'data': '取消分享成功！'
    })


# 生成随机提取码
def random_code():
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    return random_string
