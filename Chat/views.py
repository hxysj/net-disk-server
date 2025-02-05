import uuid
import json
from django.http import JsonResponse
from Chat.serializers import ConverSationsUserSerializers, MessageSerializers
from tools.logging_dec import logging_check
from Chat.models import ConverSationsUser, Message, ConverSations
from django.db.models import Q
from User.models import User
from django.utils import timezone
from django.core.cache import cache


@logging_check
def get_session(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'get session for user is error'
        }, status=400)

    user = request.my_user
    try:
        session_list = ConverSationsUser.objects.filter(user_id=user).select_related('user_id', 'conversation_id')
    except Exception as e:
        print(f'get session is error : {e}')
        return JsonResponse({
            'error': 'get session for user is error'
        }, status=400)
    session_list = ConverSationsUserSerializers(session_list, many=True).data

    result_list = []
    for session in session_list:
        is_user1 = session['user1_name'] == user.nick_name
        noReadCount = Message.objects.filter(conversation_id=session['conversation_id'], status=0,
                                             user_id=session['user2_id'] if is_user1 else session['user1_id']).count()
        try:
            # 获取会话对象
            conversation = ConverSations.objects.get(conversation_id=session['conversation_id'])
            delete_at = (conversation.user1_delete_at if is_user1 else conversation.user2_delete_at)
            lastMessage = Message.objects.filter(
                Q(conversation_id=session['conversation_id']) & Q(create_time__gt=delete_at)).latest(
                'create_time')
            last_message_content = lastMessage.content
            last_message_time = lastMessage.create_time
        except Exception as e:
            last_message_content = ""
            last_message_time = None

        result_list.append({
            'user_id': session['user2_id'] if is_user1 else session['user1_id'],
            'nick_name': session['user2_name'] if is_user1 else session['user1_name'],
            'avatar': session['user2_avatar'] if is_user1 else session['user1_avatar'],
            'last_message_content': last_message_content,
            'last_message_time': last_message_time,
            'conversation_id': session['conversation_id'],
            'new_message': noReadCount
        })
    return JsonResponse({
        'code': 10000,
        'list': result_list
    })


@logging_check
def get_message(request):
    if request.method != 'GET':
        return JsonResponse({
            'error': 'get message for session id is error'
        }, status=400)
    session_id = request.GET.get('session_id')
    user = request.my_user
    try:
        # 获取会话对象
        conversation = cache.get(f'conversation_data_{session_id}')
        if not conversation:
            conversation = ConverSations.objects.get(conversation_id=session_id)
            cache.set(f'conversation_data_{session_id}', conversation, 60 * 60 * 24 * 7)

        # 根据当前用户选择相应的删除时间字段
        delete_at = (
            conversation.user1_delete_at if user.user_id == conversation.user1.user_id
            else conversation.user2_delete_at
        )

        # 构建查询条件
        filters = Q(conversation_id=conversation)
        if delete_at:
            filters &= Q(create_time__gt=delete_at)
        message_list = cache.get(f'message_list_{user.user_id}_{session_id}')
        if not message_list:
            # 获取消息列表
            message_list = Message.objects.filter(filters).order_by('create_time')
            cache.set(f'message_list_{user.user_id}_{session_id}', message_list, 60 * 60 * 24 * 7)
    except Exception as e:
        print(f'get message is error: {e}')
        return JsonResponse({
            'error': 'get message for session id is error'
        }, status=400)
    message_list = MessageSerializers(message_list, many=True).data
    # print(66, message_list)
    num = int(request.GET.get('num', 0))  # 默认读取尾部
    limit = 20  # 每次读取数据的条数
    # 计算起始和结束位置
    start = -num  # 计算查询的起始位置
    end = -(limit + num)  # 计算查询的结束位置
    if start == 0:
        show_list = message_list[-limit:]
    else:
        show_list = message_list[end:start]
    return JsonResponse({
        'code': 200,
        'list': show_list
    })


@logging_check
def set_read_message(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'set message is read is error'
        }, status=400)
    data = json.loads(request.body)
    conversation_id = data.get('session_id')
    try:
        conversation = cache.get(f'conversation_data_{conversation_id}')
        if not conversation:
            conversation = ConverSations.objects.get(conversation_id=conversation_id)
            cache.set(f'conversation_data_{conversation_id}', conversation, 60 * 60 * 24 * 7)
    except Exception as e:
        print(e)
        return JsonResponse({
            'error': 'set message is read is error'
        }, status=400)
    Message.objects.filter(conversation_id=conversation, status=0).exclude(user_id=request.my_user).update(status=1)
    cache.delete(f'message_list_{request.my_user.user_id}_{conversation_id}')
    return JsonResponse({
        'code': 1000,
        'status': 'success'
    })


@logging_check
def create_session(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'create session is error'
        }, status=400)
    user1_id = request.POST.get('user')
    try:
        user1 = User.objects.get(user_id=user1_id)
    except Exception as e:
        print(f'create session && find user is error: {e}')
        return JsonResponse({
            'error': 'find user is error'
        }, status=400)
    user2 = request.my_user

    try:
        conversation = ConverSations.objects.get(
            Q(user1_id=user1, user2_id=user2) | Q(user1_id=user2, user2_id=user1)
        )
    except Exception as e:
        session_id = uuid.uuid4()
        conversation = ConverSations.objects.create(
            conversation_id=session_id,
            user1=user1,
            user2=user2
        )
        cache.set(f'conversation_data_{session_id}', conversation, 60 * 60 * 24 * 7)

    try:
        if not cache.get(f'conversations_user_{user2.user_id}_{conversation.conversation_id}'):
            conversation_user = ConverSationsUser.objects.get(conversation_id=conversation, user_id=user2)
            cache.set(f'conversations_user_{user2.user_id}_{conversation.conversation_id}', conversation_user,
                      60 * 60 * 24 * 7)
    except Exception as e:
        conversation_user = ConverSationsUser.objects.create(
            conversation_id=conversation,
            user_id=user2
        )
        cache.set(f'conversations_user_{user2.user_id}_{conversation.conversation_id}', conversation_user,
                  60 * 60 * 24 * 7)

    return JsonResponse({
        'code': 10000,
        'message': 'create conversations is success',
        'conversation_id': conversation.conversation_id
    })


@logging_check
def clear_chat_record(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': 'clear chat record is error'
        })
    user = request.my_user
    friend_id = (json.loads(request.body)).get('uid')
    friend = User.objects.get(user_id=friend_id)

    try:
        conversation = ConverSations.objects.get(Q(user1=user, user2=friend) | Q(user2=user, user1=friend))
        conversations_user = cache.get(f'conversations_user_{user.user_id}_{conversation.conversation_id}')
        if not conversations_user:
            conversations_user = ConverSationsUser.objects.get(conversation_id=conversation, user_id=user)
            cache.set(f'conversations_user_{user.user_id}_{conversation.conversation_id}', conversations_user,
                      60 * 60 * 24 * 7)
    except Exception as e:
        print('clear_chat_record', e)
        return JsonResponse({
            'code': 10000,
            'status': 'success',
            'message': 'not found message to delete'
        })
    if user == conversation.user1:
        conversation.user1_delete_at = timezone.now()
    else:
        conversation.user2_delete_at = timezone.now()
    conversation.save()
    conversations_user.delete()
    cache.delete(f'conversation_data_{conversation.conversation_id}')
    cache.delete(f'conversations_user_{user.user_id}_{conversation.conversation_id}')
    Message.objects.filter(conversation_id=conversation, status=0).exclude(user_id=request.my_user).update(status=1)
    cache.delete(f'message_list_{user.user_id}_{conversation.conversation_id}')
    return JsonResponse({
        'code': 10000,
        'status': 'success'
    })
