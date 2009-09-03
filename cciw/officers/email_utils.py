from django.core.mail import EmailMessage, SMTPConnection
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.hashcompat import sha_constructor
from cciw.cciwmain import utils
"""
Utilities for sending email with attachments
"""

def send_mail_with_attachments(subject, message, from_email,
                               recipient_list, fail_silently=False,
                               auth_user=None, auth_password=None,
                               attachments=None):
    connection = SMTPConnection(username=auth_user, password=auth_password,
                                 fail_silently=fail_silently)
    return EmailMessage(subject=subject, body=message, from_email=from_email,
                        to=recipient_list, connection=connection, attachments=attachments).send()

def formatted_email(user):
    """
    Get the email address plus name of the user, formatted for
    use in sending an email, or 'None' if no email address available
    """
    name = (u"%s %s" % (user.first_name, user.last_name)).strip().replace(u'"', u'')
    email = user.email.strip()
    if len(email) == 0:
        return None
    elif len(name) > 0:
        return u'"%s" <%s>' % (name, email)
    else:
        return email

def make_update_email_hash(oldemail, newemail):
    """
    Returns a hash for use in confirmation of e-mail change.
    """
    return sha_constructor("emailupdate" + settings.SECRET_KEY + ':' + oldemail + ':' + newemail).hexdigest()[::2]

def make_ref_form_url_hash(ref_id, prev_ref_id):
    return sha_constructor("create_reference_form%s:%s:%s" % (settings.SECRET_KEY, ref_id, prev_ref_id)).hexdigest()[::2]

def make_ref_form_url(ref_id, prev_ref_id):
    if prev_ref_id is None: prev_ref_id = ""
    return  "https://%s%s" % (utils.get_current_domain(),
                               reverse('cciw.officers.views.create_reference_form',
                                       kwargs=dict(ref_id=ref_id,
                                                   prev_ref_id=prev_ref_id,
                                                   hash=make_ref_form_url_hash(ref_id, prev_ref_id))))


def send_reference_request_email(message, ref):
    officer = ref.application.officer
    send_mail_with_attachments("Reference for %s %s" % (officer.first_name, officer.last_name),
                               message,
                               settings.DEFAULT_FROM_EMAIL,
                               [ref.referee.email],
                               fail_silently=False)
