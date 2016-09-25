from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from .lists import handle_mail
from .mailgun import verify


def b(s):
    return bytes(s, 'ascii')


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
