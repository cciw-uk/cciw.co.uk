# Mailgun specify things.

import hmac
import hashlib

from django.utils.crypto import constant_time_compare


# See https://documentation.mailgun.com/user_manual.html#securing-webhooks
def verify(api_key, token, timestamp, signature):
    return constant_time_compare(signature,
                                 hmac.new(
                                     key=api_key,
                                     msg=timestamp + token,
                                     digestmod=hashlib.sha256).hexdigest())
