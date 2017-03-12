import email
import json
from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from requests.structures import CaseInsensitiveDict

from cciw.officers.email import X_REFERENCE_REQUEST, handle_reference_bounce

from . import X_CCIW_ACTION, X_CCIW_CAMP
from .lists import handle_mail_async
from .mailgun import verify_webhook
from .models import EmailNotification


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
    data = request.POST['body-mime']
    # If we handle mail within the request/response cycle, we can easily end up
    # with timeouts - e.g. a 5 Mb attachment that gets sent to 30 people has to
    # be sent 30 times back to Mailgun. So we save and deal with it
    # asynchronously.
    handle_mail_async(data.encode('utf-8'))
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


def make_mailgun_notification_handler(required_event):

    @csrf_exempt
    @ensure_from_mailgun
    def mailgun_notification(request):
        event = request.POST['event']
        if event != required_event:
            return HttpResponseBadRequest("Expecting event == {0}, not {1}".format(
                required_event, event))
        EmailNotification.log_event(email=request.POST['recipient'],
                                    event=event,
                                    data=request.POST.items())
        return HttpResponse('OK!')
    return mailgun_notification


mailgun_drop_notification = make_mailgun_notification_handler('dropped')
mailgun_deliver_notification = make_mailgun_notification_handler('delivered')
