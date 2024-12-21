from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse


# 生产scrf令牌
@ensure_csrf_cookie
def csrf_token(request):
    # print(request.META['CSRF_COOKIE'])
    response = JsonResponse({
        'csrfToken': request.META['CSRF_COOKIE']
    })
    response.set_cookie('csrftoken', request.META['CSRF_COOKIE'], 60 * 60 * 24)
    return response
