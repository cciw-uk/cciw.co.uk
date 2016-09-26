from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from .lists import handle_mail
from .mailgun import verify_webhook


def b(s):
    return bytes(s, 'ascii')


def ensure_from_mailgun(f):
    @wraps(f)
    def func(request, *args, **kwargs):
        if not verify_webhook(
                b(settings.MAILGUN_API_KEY),
                b(request.POST['token']),
                b(request.POST['timestamp']),
                b(request.POST['signature'])):
            return HttpResponseForbidden("Not a real Mailgun request, ignoring.")

        # We should really do something to prevent replay attacks. However,
        # since Mailgun will post to us over HTTPS, it would be very hard for an
        # attacker to get a payload that they could replay.

        return f(request, *args, **kwargs)
    return func


@csrf_exempt
@ensure_from_mailgun
def mailgun_incoming(request):
    # TODO - handle email that is too big (25 Mb limit). We could send back a
    # 406 response to Mailgun, and send an explanation to sender.
    handle_mail(request.POST['body-mime'])
    return HttpResponse('OK!')
