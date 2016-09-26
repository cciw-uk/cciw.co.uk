import email
import json
from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from requests.structures import CaseInsensitiveDict

from cciw.officers.email import X_REFERENCE_REQUEST, handle_reference_bounce

from . import X_CCIW_ACTION, X_CCIW_CAMP
from .lists import handle_mail
from .mailgun import verify_webhook


def b(s):
    return bytes(s, 'ascii')


def ensure_from_mailgun(f):
    @wraps(f)
    def func(request, *args, **kwargs):
        if not verify_webhook(
                b(settings.MAILGUN_API_KEY),
                b(request.POST.get('token', '')),
                b(request.POST.get('timestamp', '')),
                b(request.POST.get('signature', ''))):
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


@csrf_exempt
@ensure_from_mailgun
def mailgun_bounce_notification(request):
    message_headers = CaseInsensitiveDict(json.loads(request.POST['message-headers']))
    cciw_action = message_headers.get(X_CCIW_ACTION, '')
    reply_to = message_headers.get('Reply-To',
                                   message_headers['From'])
    recipient = request.POST['recipient']
    original_message = email.message_from_bytes(request.FILES['attachment-1'].read())

    if cciw_action == X_REFERENCE_REQUEST:
        camp_name = message_headers.get(X_CCIW_CAMP, '')
        handle_reference_bounce(recipient, reply_to, original_message, camp_name)

    return HttpResponse('OK!')
