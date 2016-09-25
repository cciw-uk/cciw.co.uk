from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .lists import handle_mail
from functools import wraps

import hmac
import hashlib

from django.utils.crypto import constant_time_compare


def b(s):
    return bytes(s, 'ascii')


# See https://documentation.mailgun.com/user_manual.html#securing-webhooks
def verify(api_key, token, timestamp, signature):
    return constant_time_compare(signature,
                                 hmac.new(
                                     key=api_key,
                                     msg=timestamp + token,
                                     digestmod=hashlib.sha256).hexdigest())


def ensure_from_mailgun(f):
    @wraps(f)
    def func(request, *args, **kwargs):
        if not verify(
                b(settings.MAILGUN_API_KEY),
                b(request.POST['token']),
                b(request.POST['timestamp']),
                b(request.POST['signature'])):
            return HttpResponseForbidden("Not a real Mailgun request, ignoring.")
        # TODO - prevent replay attacks.

        return f(request, *args, **kwargs)
    return func


@csrf_exempt
@ensure_from_mailgun
def mailgun_incoming(request):
    handle_mail(request.POST['body-mime'].encode('utf-8'))
    return HttpResponse('OK!')
