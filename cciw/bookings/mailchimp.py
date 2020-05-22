import hashlib

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth


def update_newsletter_subscription(booking_account):
    status = get_status(booking_account)
    if booking_account.subscribe_to_newsletter:
        if status is None or status != "subscribed":
            return _update(booking_account, status, "subscribed")
    else:
        if status is not None and (status in ["subscribed", "pending"]):
            return _update(booking_account, status, "unsubscribed")
    return None


def _update(booking_account, current_status, desired_status):
    if current_status is None:
        return mailchimp_request('POST', f'/lists/{settings.MAILCHIMP_NEWSLETTER_LIST_ID}/members/',
                                 json={
                                     "email_address": booking_account.email,
                                     "status": desired_status,
                                 })
    else:
        mailchimp_id = email_to_mailchimp_id(booking_account.email)
        return mailchimp_request('PATCH', f'/lists/{settings.MAILCHIMP_NEWSLETTER_LIST_ID}/members/{mailchimp_id}',
                                 json={
                                     "status": desired_status,
                                 })


def email_to_mailchimp_id(email):
    return hashlib.md5(email.lower().encode('utf-8')).hexdigest()


def get_status(booking_account):
    id = email_to_mailchimp_id(booking_account.email)
    response = mailchimp_request_unchecked('GET',
                                           '/lists/{0}/members/{1}'.format(
                                               settings.MAILCHIMP_NEWSLETTER_LIST_ID,
                                               id))
    if response.status_code == 404:
        return None

    return response.json()['status']


def mailchimp_request_unchecked(method, path, **kwargs):
    url = settings.MAILCHIMP_URL_BASE + path
    auth = HTTPBasicAuth('user', settings.MAILCHIMP_API_KEY)
    return requests.request(method, url, auth=auth, **kwargs)


def mailchimp_request(*args, **kwargs):
    response = mailchimp_request_unchecked(*args, **kwargs)
    if response.status_code != 200:
        raise Exception("Mailchimp returned {0}: {1}".format(response.status_code,
                                                             response.json()['detail']))
    return response
