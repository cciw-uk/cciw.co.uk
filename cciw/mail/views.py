import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from requests.structures import CaseInsensitiveDict

from cciw.aws import confirm_sns_subscriptions, ensure_from_aws_sns
from cciw.officers.email import X_REFERENCE_REQUEST, handle_reference_bounce

from . import X_CCIW_ACTION, X_CCIW_CAMP
from .lists import handle_mail_async
from .ses import download_ses_message_from_s3


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
    handle_mail_async(data, message_id=message_id)
    return HttpResponse('OK!')


@csrf_exempt
@ensure_from_aws_sns
@confirm_sns_subscriptions
def ses_bounce_notification(request):
    message = json.loads(json.loads(request.body)['Message'])
    message_headers = CaseInsensitiveDict({
        h['name']: h['value']
        for h in message['mail']['headers']
    })

    cciw_action = message_headers.get(X_CCIW_ACTION, '')
    reply_to = message_headers.get('Reply-To',
                                   message_headers['From'])
    recipient = message_headers['To']

    if cciw_action == X_REFERENCE_REQUEST:
        camp_name = message_headers.get(X_CCIW_CAMP, '')
        handle_reference_bounce(recipient, reply_to, None, camp_name)

    return HttpResponse('OK!')
