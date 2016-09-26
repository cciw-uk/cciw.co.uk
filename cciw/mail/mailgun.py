# Mailgun specific things.

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


def api_request(path, data=None, files=None, method=None, add_domain=False):
    domain = settings.MAILGUN_DOMAIN
    url = "https://api.mailgun.net/v3"
    if add_domain:
        url += "/" + domain
    url += path

    if method is None:
        if data is None and files is None:
            method = 'get'
        else:
            method = 'post'

    response = requests.request(
        method,
        url,
        auth=("api", settings.MAILGUN_API_KEY),
        data=data,
        files=files)
    response.raise_for_status()
    return response.json()


# Emails that we generate are sent using the anymail Mailgun backend, via
# EMAIL_BACKEND. But for MIME messages that we are modifying and forwarding, we
# need to use send_mime_message.

def send_mime_message(to, mime_message):
    return api_request('/messages.mime',
                       add_domain=True,
                       data={"to": to},
                       files={"message": BytesIO(mime_message)})


def list_routes():
    return api_request('/routes', add_domain=False)


def create_route(description, expression, actions):
    return api_request('/routes',
                       data=dict(description=description,
                                 expression=expression,
                                 action=actions))


def update_route(id, description, expression, actions):
    return api_request('/routes/{0}'.format(id),
                       method='put',
                       data=dict(description=description,
                                 expression=expression,
                                 action=actions))
