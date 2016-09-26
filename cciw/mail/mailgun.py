# Mailgun specify things.

import hashlib
import hmac
from io import BytesIO

import requests
from django.conf import settings
from django.utils.crypto import constant_time_compare


# See https://documentation.mailgun.com/user_manual.html#securing-webhooks
def verify_webhook(api_key, token, timestamp, signature):
    return constant_time_compare(signature,
                                 hmac.new(
                                     key=api_key,
                                     msg=timestamp + token,
                                     digestmod=hashlib.sha256).hexdigest())


def api_request(path, data, files):
    domain = settings.MAILGUN_DOMAIN
    return requests.post(
        "https://api.mailgun.net/v3/{0}/{1}".format(domain, path),
        auth=("api", settings.MAILGUN_API_KEY),
        data=data,
        files=files)


def send_mime_message(to, mime_message):
    return api_request('messages.mime',
                       data={"to": to},
                       files={"message": BytesIO(mime_message)})
