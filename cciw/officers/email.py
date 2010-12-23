from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_difference
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from cciw.officers.references import reference_form_to_text
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.utils.crypto import salted_hmac
import cciw.middleware.threadlocals as threadlocals
import urllib

def make_update_email_hash(oldemail, newemail):
    """
    Returns a hash for use in confirmation of e-mail change.
    """
    return salted_hmac("cciw.officers.emailupdate", oldemail + ':' + newemail).hexdigest()[::2]

def admin_emails_for_application(application):
    leaders = [user for leader in application.camp.leaders.all()
                    for user in leader.users.all()] + \
              list(application.camp.admins.all())
    return filter(lambda x: x is not None,
                  map(formatted_email, leaders))

def send_application_emails(request, application):
    if not application.finished:
        return

    # Email to the leaders:
    # Collect e-mails to send to
    leader_emails = admin_emails_for_application(application)

    application_text = application_to_text(application)
    application_rtf = application_to_rtf(application)
    rtf_attachment = (application_rtf_filename(application), application_rtf, 'text/rtf')

    # Did the officer submit one last year for the 'same' camp?
    previous_camp = application.camp.previous_camp
    application_diff = None
    if previous_camp is not None:
        officer = application.officer
        try:
            previous_app = officer.application_set.filter(camp=previous_camp, finished=True)[0]
        except IndexError:
            previous_app = None
        if previous_app is not None:
            application_diff = ("differences_from_last_year.html",
                                application_difference(previous_app, application),
                                "text/html")

    if len(leader_emails) > 0:
        send_leader_email(leader_emails, application, application_text, rtf_attachment,
                          application_diff)
        messages.info(request, "The completed application form has been sent to the leaders via e-mail.")

    # If an admin user corrected an application, we don't send the user a copy
    # (usually they just get the year of the camp wrong(!))
    if request.user == application.officer:
        send_officer_email(application.officer, application, application_text, rtf_attachment)
        messages.info(request, "A copy of the application form has been sent to you via e-mail.")

        if application.officer.email.lower() != application.address_email.lower():
            send_email_change_emails(application.officer, application)

def send_officer_email(officer, application, application_text, rtf_attachment):
    subject = "CCIW application form submitted"

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = (
u"""%s,

For your records, here is a copy of the application you have submitted
to CCIW. It is also attached to this e-mail as an RTF file.

""" % application.officer.first_name) + application_text

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL,
                                   [user_email], attachments=[rtf_attachment])

def send_leader_email(leader_emails, application, application_text, rtf_attachment,
                      application_diff):
    subject = "CCIW application form from %s" % application.full_name
    body = \
u"""The following application form has been submitted via the
CCIW website.  It is also attached to this e-mail as an RTF file.

"""
    if application_diff is not None:
        body += \
u"""The second attachment shows the differences between this year's
application form and last year's - pink indicates information that has
been removed, green indicates new information.

"""

    officer = application.officer
    if not officer.invitation_set.filter(camp=application.camp).exists():
        body += \
u"""PLEASE NOTE: %s %s is not currently on your officer list. It is
important for CRB records and other purposes that you add this officer
to your officer list if they will be coming on camp.

""" % (officer.first_name, officer.last_name)

    body += application_text

    attachments = [rtf_attachment]
    if application_diff is not None:
        attachments.append(application_diff)

    send_mail_with_attachments(subject, body, settings.SERVER_EMAIL,
                               leader_emails, attachments=attachments)

def make_update_email_url(application):
    email = application.address_email
    old_email = application.officer.email
    return 'https://%(domain)s%(path)s?email=%(email)s&hash=%(hash)s' % dict(domain=common.get_current_domain(),
                                                                           path=reverse('cciw.officers.views.update_email', kwargs={'username': application.officer.username}),
                                                                           email=urllib.quote(email),
                                                                           hash=make_update_email_hash(old_email, email))

def send_email_change_emails(officer, application):
    subject = "E-mail change on CCIW"
    user_email = formatted_email(officer)
    user_msg = (
u"""%(name)s,

In your most recently submitted application form, you entered your
e-mail address as %(new)s.  The e-mail address stored against your
account is %(old)s.  If you would like this to be updated to '%(new)s'
then click the link below:

 %(url)s

If the e-mail address you entered on your application form (%(new)s)
is, in fact, incorrect, then please reply to this e-mail to say so.

NB. This e-mail has been sent to both the old and new e-mail
addresses, you only need to respond to one e-mail.

Thanks,


This was an automated response by the CCIW website.


""" % dict(name=officer.first_name, old=officer.email,
           new=application.address_email, url=make_update_email_url(application))
        )

    send_mail(subject, user_msg, settings.SERVER_EMAIL,
              [user_email, application.address_email] , fail_silently=True)

def make_ref_form_url_hash(ref_id, prev_ref_id):
    return salted_hmac("cciw.officers.create_reference_form", "%s:%s" % (ref_id, prev_ref_id)).hexdigest()[::2]

def make_ref_form_url(ref_id, prev_ref_id):
    if prev_ref_id is None: prev_ref_id = ""
    return  "https://%s%s" % (common.get_current_domain(),
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

def send_leaders_reference_email(refform):
    """
    Send the leaders/admins an email with contents of submitted reference form.
    Fails silently.
    """
    ref = refform.reference_info
    app = ref.application
    officer = app.officer

    leader_emails = admin_emails_for_application(app)
    refform_text = reference_form_to_text(refform)
    subject = "CCIW reference form for %s %s from %s" % (officer.first_name, officer.last_name, ref.referee.name)
    body = \
u"""The following reference form has been submitted via the
CCIW website for officer %s %s.

%s
""" % (officer.first_name, officer.last_name, refform_text)

    send_mail(subject, body, settings.SERVER_EMAIL,
              leader_emails, fail_silently=False)
