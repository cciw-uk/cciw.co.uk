import email
import json
from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from requests.structures import CaseInsensitiveDict

from cciw.aws import confirm_sns_subscriptions, ensure_from_aws_sns
from cciw.officers.email import X_REFERENCE_REQUEST, handle_reference_bounce

from . import X_CCIW_ACTION, X_CCIW_CAMP
from .lists import handle_mail_async
from .mailgun import verify_webhook
from .ses import download_ses_message_from_s3


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


@csrf_exempt
@ensure_from_aws_sns
@confirm_sns_subscriptions
def ses_incoming_notification(request):
    # @confirm_sns_subscriptions has handled other message types
    data = json.loads(request.body)
    message_id = json.loads(data['Message'])['mail']['messageId']
    # If we handle mail within the request/response cycle, we can easily end up
    # with timeouts - e.g. a 5 Mb attachment that gets sent to 30 people has to
    # be sent 30 times. So we save and deal with it asynchronously.
    data = download_ses_message_from_s3(message_id)
    handle_mail_async(data)
    return HttpResponse('OK!')


@csrf_exempt
@ensure_from_aws_sns
@confirm_sns_subscriptions
def ses_bounce_notification(request):
    message = json.loads(json.loads(request.body)['Message'])
    message_headers = CaseInsensitiveDict({
        h['name']: h['value']
        for h in
        message['mail']['headers']
    })

    cciw_action = message_headers.get(X_CCIW_ACTION, '')
    reply_to = message_headers.get('Reply-To',
                                   message_headers['From'])
    recipient = message_headers['To']

    if cciw_action == X_REFERENCE_REQUEST:
        camp_name = message_headers.get(X_CCIW_CAMP, '')
        handle_reference_bounce(recipient, reply_to, None, camp_name)

    return HttpResponse('OK!')


# TODO - need equivalent of setup_mailgun_routes for SES,
#        to create rules for our mailing lists
# TODO - need to re-setup rules each time new camps are added.
# TODO - mechanism for other abitrary email
#        addresses (DB). Fill in from mailgun_routes.json
