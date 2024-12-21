# -*- codeing = utf-8 -*-
# @Time : 2024/9/21 20:31
# @Author : °。零碎゛記忆
# @File : utils.py
# @Software : PyCharm
from FileInfo.models import FileInfo
import uuid
from django.core.cache import cache


# 检测请求的pid是否存在祖宗中  file_id 当前文件的id，pid被检测的id
def check_file_id(file_id, pid, user):
    if file_id == pid:
        return True
    # print('share-file:', file_id)
    # print('pid:', pid)

    if cache.get(f'file_user_list_${user.user_id}_${file_id}'):
        file_list = cache.get(f'file_user_list_${user.user_id}_${file_id}')
    else:
        file_list = FileInfo.objects.filter(file_pid=file_id, user_id=user)
        cache.set(f'file_user_list_${user.user_id}_${file_id}', file_list, 60*60*24)
    if len(file_list) == 0:
        return False
    file_id_list = [file.file_id for file in file_list]
    # print('file_list:', file_id_list)
    if pid in file_id_list:
        return True
    for file_p_id in file_id_list:
        if check_file_id(file_p_id, pid, user):
            return True
    return False


# 通过fileId文件id找出他的子孙后代的fileid
def search_file_children(file_id, user):
    result = {
        'fileId': file_id,
        'children': []
    }
    if cache.get(f'file_user_list_${user.user_id}_${file_id}'):
        file_list = cache.get(f'file_user_list_${user.user_id}_${file_id}')
    else:
        file_list = FileInfo.objects.filter(file_pid=file_id, user_id=user)
        cache.set(f'file_user_list_${user.user_id}_${file_id}', file_list, 60*60*24)
    if len(file_list) == 0:
        return result
    for file in file_list:
        result['children'].append(search_file_children(file.file_id, user))

    return result


# 去除search_file_children 获得的格式中的fileid 变成一个一维数组
def get_search_file_list(list):
    result = []
    for ls in list:
        result.append(ls['fileId'])
        if len(ls['children']) != 0:
            result += get_search_file_list(ls['children'])
    return result


# 计算总文件大小
def sum_file_size(obj):
    size = 0
    if cache.get(f'file_info_${obj["fileId"]}'):
        file = cache.get(f'file_info_${obj["fileId"]}')
    else:
        file = FileInfo.objects.get(file_id=obj['fileId'])
        cache.set(f'file_info_${file.file_id}', file, 60*60*24)
    if file.folder_type != 1:
        size += file.file_size
    if len(obj['children']) != 0:
        for child_file in obj['children']:
            size += sum_file_size(child_file)
    return size


# 复制文件保存到自己网盘  obj = {file_id,children:[]}  user要保存到网盘的用户  pid  保存的位置的file_id
def copy_file(obj, user, pid):
    if cache.get(f'file_info_${obj["fileId"]}'):
        file = cache.get(f'file_info_${obj["fileId"]}')
    else:
        file = FileInfo.objects.get(file_id=obj['fileId'])
        cache.set(f'file_info_${obj["fileId"]}', file, 60*60*24)
    new_file_id = uuid.uuid4()
    FileInfo.objects.create(file_id=new_file_id,
                            file_pid=pid,
                            user_id=user,
                            file_md5=file.file_md5,
                            file_size=file.file_size,
                            file_name=file.file_name,
                            file_cover=file.file_cover,
                            file_path=file.file_path,
                            folder_type=file.folder_type,
                            file_category=file.file_category,
                            file_type=file.file_type,
                            status=file.status
                            )
    if cache.get(f'file_user_list_${user.user_id}_${pid}'):
        cache.delete(f'file_user_list_${user.user_id}_${pid}')
    for file_child in obj['children']:
        copy_file(file_child, user, new_file_id)
