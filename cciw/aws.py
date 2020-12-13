# -*- coding: utf-8 -*-
# AWS utilities
#
# See
# https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
##
# Thanks to https://gist.github.com/amertkara/e294562759ff2755486e

import json
import logging
from base64 import b64decode
from functools import lru_cache, wraps

import furl
import requests
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.http import HttpResponse

logger = logging.getLogger(__name__)

SNS_MESSAGE_TYPE_SUB_NOTIFICATION = "SubscriptionConfirmation"
SNS_MESSAGE_TYPE_NOTIFICATION = "Notification"
SNS_MESSAGE_TYPE_UNSUB_NOTIFICATION = "UnsubscribeConfirmation"


def canonical_message_builder(content, fields):
    """ Builds the canonical message to be verified.
        Sorts the fields as a requirement from AWS
        Args:
            content (dict): Parsed body of the response
            format (list): List of the fields that need to go into the message
        Returns (str):
            canonical message
    """
    return ''.join(
        field + "\n" + content[field] + "\n"
        for field in sorted(fields)
        if field in content
    ).encode('ascii')


def verify_sns_notification(request):
    """ Takes a notification request from Amazon push service SNS and verifies the origin of the notification.
        Kudos to Artur Rodrigues for suggesting M2Crypto: http://goo.gl/KAgPPc
        Args:
            request (HTTPRequest): The request object that is passed to the view function
        Returns (bool):
            True if he message passes the verification, False otherwise
        Raises:
            ValueError: If the body of the response couldn't be parsed
            M2CryptoError: If an error raises during the verification process
            URLError: If the SigningCertURL couldn't be opened
    """
    cert = None
    pubkey = None
    canonical_message = None
    canonical_sub_unsub_format = ["Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"]
    canonical_notification_format = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]

    content = json.loads(request.body)
    decoded_signature = b64decode(content["Signature"])

    signing_cert_url = content["SigningCertURL"]
    if not furl.furl(signing_cert_url).host.endswith('.amazonaws.com'):
        return False

    msg_type = request.headers.get("X-Amz-Sns-Message-Type", None)
    # Depending on the message type, canonical message format varies: http://goo.gl/oSrJl8
    if msg_type == SNS_MESSAGE_TYPE_SUB_NOTIFICATION or msg_type == SNS_MESSAGE_TYPE_UNSUB_NOTIFICATION:
        canonical_message = canonical_message_builder(content, canonical_sub_unsub_format)
    elif msg_type == SNS_MESSAGE_TYPE_NOTIFICATION:
        canonical_message = canonical_message_builder(content, canonical_notification_format)
    else:
        raise ValueError(f"Message Type {msg_type} is not recognized")

    # Load the certificate and extract the public key
    cert = x509.load_pem_x509_certificate(load_resource_cached(signing_cert_url))
    pubkey = cert.public_key()
    try:
        pubkey.verify(decoded_signature, canonical_message, padding.PKCS1v15(), hashes.SHA1())
        return True
    except InvalidSignature:
        return False


@lru_cache(maxsize=100)
def load_resource_cached(url):
    logger.info(f'Downloading {url}')
    return requests.get(url).content


def ensure_from_aws_sns(view_func):
    @wraps(view_func)
    def wrapper(request):
        if not verify_sns_notification(request):
            return HttpResponse('Invalid signature', status=400)
        return view_func(request)
    return wrapper


def confirm_sns_subscriptions(view_func):
    @wraps(view_func)
    def wrapper(request):
        msg_type = request.headers.get("X-Amz-Sns-Message-Type", None)
        if msg_type == SNS_MESSAGE_TYPE_SUB_NOTIFICATION:
            subscribe_url = json.loads(request.body)["SubscribeURL"]
            logger.info(f'Accessing {subscribe_url}')
            requests.get(subscribe_url)
            return HttpResponse('Subscribed')
        else:
            return view_func(request)
    return wrapper
