# -*- codeing = utf-8 -*-
# @Time : 2024/9/21 20:31
# @Author : °。零碎゛記忆
# @File : utils.py
# @Software : PyCharm
from FileInfo.models import FileInfo
import uuid
from django.core.cache import cache
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import random
import string

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


# 用于生成验证码
def generate_captcha():
    # 创建一个空白图像（白色背景，宽100px，高35px）
    image = Image.new('RGB', (50, 15), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 选择字体（根据系统，可能需要指定字体文件的路径）
    try:
        font = ImageFont.truetype("../static/font/GenShinGothic-Monospace-Regular.ttf", 50)
    except IOError:
        font = ImageFont.load_default()

    # 随机生成验证码文本
    captcha_text = ''.join(random.choices(string.ascii_letters + string.digits, k=4))

    # 计算文本的边界框，获取宽度和高度
    bbox = draw.textbbox((0, 0), captcha_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 计算文本位置，确保居中
    text_x = (image.width - text_width) // 2
    text_y = (image.height - text_height) // 2

    # 在图像上绘制验证码
    draw.text((text_x, text_y), captcha_text, font=font, fill=(0, 0, 0))

    # 添加背景噪点（干扰点）
    for _ in range(50):
        x = random.randint(0, image.width)
        y = random.randint(0, image.height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

    # 添加干扰线
    for _ in range(2):
        x1 = random.randint(0, image.width)
        y1 = random.randint(0, image.height)
        x2 = random.randint(0, image.width)
        y2 = random.randint(0, image.height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                  width=2)

    # 将图像保存到内存中（用 BytesIO）
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')

    # 转换为 base64 编码
    img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

    # 返回生成的验证码文本和图像的 Base64 数据
    return captcha_text, img_base64