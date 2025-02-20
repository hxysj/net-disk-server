import json
import os
import threading
import uuid
from django.db.models import Q
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core.cache import cache

# 导入模型之前初始化settings的设置
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netDisk.settings')
django.setup()

from FileInfo.models import FileInfo
from Chat.models import Message, ConverSations, ConverSationsUser
from User.models import Friend
from utils.utils import get_file_type, decrypt_data
from asgiref.sync import sync_to_async
from io import BytesIO
import shutil
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
import subprocess
from PIL import Image
import io
import re
from channels.db import database_sync_to_async


@sync_to_async
def get_file_md5(md5):
    return list(FileInfo.objects.filter(file_md5=md5).values())


@sync_to_async
def get_same_file_name(name, user):
    first_name, extension_name = os.path.splitext(name)
    return list(
        FileInfo.objects.filter(file_name__regex=rf"^{first_name}(\((\d+)\))?{extension_name}", user_id=user).values())


@sync_to_async
def create_file_info(file_id, file_md5, user, file_pid, file_size, file_name, file_category, file_type, file_cover,
                     file_path, status):
    return FileInfo.objects.create(
        file_id=file_id,
        file_md5=file_md5,
        user_id=user,
        file_pid=file_pid,
        file_size=file_size,
        file_name=file_name,
        file_cover=file_cover,
        file_path=file_path,
        folder_type=0,
        file_category=file_category,
        file_type=file_type,
        status=status
    )


@sync_to_async
def change_user_size(user, file_size):
    user.use_space += int(file_size)
    user.save()


# 对文件进行合成
def composite_file(total_chunks, file_id, file_type, content_type, file_name, file_md5):
    # 保存的根本路径
    base_dir = str(settings.BASE_DIR)
    # 创建一个 BytesIO 对象来存储合并后的文件内容
    merged_file = BytesIO()
    # 用来计算文件的md5值
    # md5_hash = hashlib.md5()
    for i in range(int(total_chunks)):
        chunk_path = f"{base_dir}/chunks/{file_id}/{file_id}_{i}"
        with open(chunk_path, 'rb') as chunk_file:
            chunk_file_content = chunk_file.read()
            # md5_hash.update(chunk_file_content)
            # 将分片内容写入Bytes IO对象
            merged_file.write(chunk_file_content)
        os.remove(chunk_path)  # 删除分片文件
    try:
        shutil.rmtree(f"{base_dir}/chunks/{file_id}")
    except Exception as e:
        print(e)
    merged_file.seek(0)

    if cache.get(f'file_info_${file_id}'):
        file = cache.get(f'file_info_${file_id}')
    else:
        try:
            file = FileInfo.objects.get(file_id=file_id)
        except Exception as e:
            print('get file is error: %s' % e)
    if file_type != 1:
        obj = create_others_file(file_type, file_id, file_name, merged_file, content_type)
    else:
        obj = create_video_file(merged_file, file_name, file_id)
    uploaded_file = obj['upload_file']
    cover_file = obj['cover']
    # print('-------->>>>>',obj)

    file.file_path = uploaded_file
    file.file_cover = cover_file
    file.status = 2
    file.save()
    cache.set(f'file_info_${file_id}', file, 60 * 60 * 24)
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
def create_video_file(merged_file, file_name, file_id):
    # print(file_name, fileId)
    # 保存的根本路径
    base_dir = str(settings.BASE_DIR)
    # 是视频文件，则合成后，对视频进行分割
    # print(file_name)
    video_path = os.path.join(base_dir, 'chunks', file_id + '.' + file_name.split('.')[-1])
    # 将视频文件保存下载 - 临时
    with open(video_path, 'wb') as f:
        # 将 BytesIO 对象的内容写入文件
        f.write(merged_file.read())
    cover_path = os.path.join(base_dir, 'chunks', file_id + '.jpg')
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
    cover_file = ContentFile(cover_content, name=file_id + '.jpg')

    # 对视频进行分割
    m3u8_path = os.path.join(base_dir, 'media', 'file', file_id + '.m3u8')
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
    m3u8_content_file = ContentFile(m3u8_content, name=file_id + '.m3u8')
    uploaded_file = m3u8_content_file
    # 删除原来生成的m3u8文件
    os.remove(m3u8_path)
    # 删除合成的视频
    os.remove(video_path)
    return {
        'cover': cover_file,
        'upload_file': uploaded_file
    }


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


class FileTransferConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.user = self.scope['user']
        except Exception as e:
            print('拒接连接', e)
            await self.close(code=401)  # 拒绝连接
            return
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            await self.send('未获得数据，请重新发送数据！')
            return
        try:
            data = json.loads(text_data)
            file_name = data.get('fileName')
            user = self.user
            chunk_file_base64 = data.get('fileBase64')
            chunk_number = data.get('chunkIndex')
            total_chunks = data.get('chunks')
            file_id = data.get('fileId')
            file_pid = data.get('filePid')
            file_md5 = data.get('fileMd5')
            file_size = data.get('fileSize')
            content_type = data.get('contentType')
        except Exception as e:
            print('获取请求的数据出现错误：', e)
            return

        # 将上传文件的消息断开
        if not cache.get(f'file_uploader_${file_id}'):
            await self.send(json.dumps({'error': '取消请求'}))
            await self.close()
            return

        if cache.get(f'file_uploader_${file_id}') == 2 or cache.get(f'file_uploader_${file_id}') == 3:
            await self.close()
            return
        if user.use_space + int(file_size) > user.total_space:
            await self.send(json.dumps({'code': 4000, 'error': '空间不足，请删除文件或拓展空间再尝试！'}))
            await self.close()
            return
        status = 'uploading'
        # 分块的名字
        chunk_name = f'{file_id}_{chunk_number}'
        try:
            file_list = await get_file_md5(file_md5)
        except Exception as e:
            print(e)
            await self.send(json.dumps({'code': 4000, 'error': 'upload file is error', 'index': chunk_number}))
            return
        file_type = get_file_type(file_name)
        if file_type <= 3:
            file_category = file_type
        elif file_type < 9:
            file_category = 4
        else:
            file_category = 5
        file_name_list = await get_same_file_name(file_name, user)
        file_name_list = [file['file_name'] for file in file_name_list]
        temp_name = get_next_filename(file_name_list)
        if temp_name:
            file_name = temp_name

        # 如果md5存在，则有相同文件，不需要进行二次上传
        if len(file_list) != 0:
            file = file_list[0]
            cache.set(f'file_uploader_${file_id}', 3, 60 * 10)
            await change_user_size(user, file_size)
            cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
            await create_file_info(file_id, file_md5, user, file_pid, file_size, file_name, file_category, file_type,
                                   file.get('file_cover', ''), file.get('file_path', ''), 2)

            cache.delete(f'file_user_list_${user.user_id}_${file_pid}')
            cache.delete(f'admin_file_list_${file_pid}')
            await self.send(json.dumps({
                'code': 10000,
                'fileId': file_id,
                'status': 'upload_seconds',
                'index': chunk_number,
                'fileName': file_name
            }))
            return
        # 对切片文件进行保存
        base_dir = str(settings.BASE_DIR)
        if not os.path.exists(os.path.join(base_dir, 'chunks', file_id)):
            os.mkdir(os.path.join(base_dir, 'chunks', file_id))
        path = os.path.join(base_dir, 'chunks', file_id, chunk_name)
        # 获取文件的base64密文
        encrypted_data = chunk_file_base64
        try:
            chunk_data = decrypt_data(encrypted_data, settings.ENCRYPTION_KEY, settings.IV_KEY)
            with open(path, 'wb') as f:
                f.write(chunk_data)
            if not cache.get(f'file_chunk_count_{file_id}'):
                count = 1
                if os.path.exists(os.path.join(base_dir, 'chunks', file_id)):
                    count = len(os.listdir(os.path.join(base_dir, 'chunks', file_id)))
                cache.set(f'file_chunk_count_{file_id}', count, 60 * 60 * 24)
        except (ValueError, KeyError) as e:
            print(e)
            await self.send(json.dumps({'code': 4000, 'error': '非法请求！', 'index': chunk_number}))
            return
        if len(os.listdir(os.path.join(base_dir, 'chunks', file_id))) == int(total_chunks):
            # 合并文件
            concat_file = threading.Thread(target=composite_file,
                                           args=(total_chunks, file_id, file_type, content_type, file_name, file_md5))

            await create_file_info(file_id, file_md5, user, file_pid, file_size, file_name, file_category, file_type,
                                   '', '', 0)
            cache.delete(f'file_user_list_${user.user_id}_${file_pid}')
            cache.delete(f'admin_file_list_${file_pid}')
            await change_user_size(user, file_size)
            cache.set(f'user_${user.user_id}', user, 60 * 60 * 24)
            concat_file.start()
            status = 'upload_finish'
        await self.send(json.dumps(
            {'code': 10000, 'status': status, 'fileId': file_id, 'index': chunk_number, 'fileName': file_name}))
        if status == 'upload_finish':
            await self.close()


class ChatMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.user = self.scope['user']
            self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
            self.room_name = f'chat_{self.conversation_id[0:20]}'
            self.room_group_name = f'chat_{self.conversation_id[0:20]}'
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            print('拒接连接', e)
            await self.close(code=401)  # 拒绝连接
            return
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        message = text_data

        is_friend = await self.check_friend_status()
        if not is_friend:
            await self.close(code=4001)
            return

        await self.save_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'message_id': str(self.message_id)
            }
        )
        await self.check_user_user_session()

    async def chat_message(self, event):
        message_id = event['message_id']
        obj = await self.get_message_user(message_id)
        message = event['message']
        await self.send(json.dumps({'content': message, 'user_id': obj.get('user_id'), 'avatar': obj.get('avatar'),
                                    'nick_name': obj.get('nick_name'), 'conversation_id': self.conversation_id,
                                    'create_time': obj.get('create_time'), 'new_message': obj.get('not_read_count')}))

    @database_sync_to_async
    def save_message(self, message):
        message_id = uuid.uuid4()
        conversation = cache.get(f'conversation_data_{self.conversation_id}')
        if not conversation:
            conversation = ConverSations.objects.get(conversation_id=self.conversation_id)
            cache.set(f'conversation_data_{self.conversation_id}', conversation, 60 * 60 * 24 * 7)
        newMessage = Message.objects.create(
            message_id=message_id,
            user_id=self.user,
            conversation_id=conversation,
            content=message,
            status=0
        )
        self.message_id = newMessage.message_id

    # 判断是否是好友关系，如果不是则不允许发送消息
    @database_sync_to_async
    def check_friend_status(self):
        conversation = cache.get(f'conversation_data_{self.conversation_id}')
        if not conversation:
            conversation = ConverSations.objects.get(conversation_id=self.conversation_id)
            cache.set(f'conversation_data_{self.conversation_id}', conversation, 60 * 60 * 24 * 7)
        try:
            if not cache.get(f'is_friend_{conversation.user1.user_id}_{conversation.user2.user_id}') and not cache.get(
                    f'is_friend_{conversation.user2.user_id}_{conversation.user1.user_id}'):
                Friend.objects.get(
                    (Q(user1=conversation.user1, user2=conversation.user2) | Q(user1=conversation.user2,
                                                                               user2=conversation.user1)) & Q(
                        status=2))
                cache.set(f'is_friend_{conversation.user1.user_id}_{conversation.user2.user_id}', True,
                          60 * 60 * 24 * 7)
                cache.set(f'is_friend_{conversation.user2.user_id}_{conversation.user1.user_id}', True,
                          60 * 60 * 24 * 7)

        except Exception as e:
            print(e)
            return False
        return True

    # 判断是否有对话，如果发送消息了没有对话就创建
    @database_sync_to_async
    def check_user_user_session(self):
        conversation = cache.get(f'conversation_data_{self.conversation_id}')
        if not conversation:
            conversation = ConverSations.objects.get(conversation_id=self.conversation_id)
            cache.set(f'conversation_data_{self.conversation_id}', conversation, 60 * 60 * 24 * 7)
        try:
            if not cache.get(f'conversations_user_{conversation.user1.user_id}_{conversation.conversation_id}'):
                ConverSationsUser.objects.get(user_id=conversation.user1, conversation_id=conversation)
        except Exception as e:
            conversation_user = ConverSationsUser.objects.create(conversation_id=conversation,
                                                                 user_id=conversation.user1)
            cache.set(f'conversations_user_{conversation.user1.user_id}_{conversation.conversation_id}',
                      conversation_user, 60 * 60 * 24 * 7)
        try:
            if not cache.get(f'conversations_user_{conversation.user2.user_id}_{conversation.conversation_id}'):
                ConverSationsUser.objects.get(user_id=conversation.user2, conversation_id=conversation)
        except Exception as e:
            conversation_user = ConverSationsUser.objects.create(conversation_id=conversation,
                                                                 user_id=conversation.user2)
            cache.set(f'conversations_user_{conversation.user2.user_id}', conversation_user, 60 * 60 * 24 * 7)

    @database_sync_to_async
    def get_message_user(self, message_id):
        message = Message.objects.get(message_id=message_id)
        receive_user_message = Message.objects.filter(status=0, conversation_id=self.conversation_id,
                                                      user_id=message.user_id).count()

        return {
            'user_id': message.user_id.user_id,
            'avatar': message.user_id.avatar.url,
            'nick_name': message.user_id.nick_name,
            'create_time': message.create_time.isoformat(),
            'not_read_count': receive_user_message
        }
