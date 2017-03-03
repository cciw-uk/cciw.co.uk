import logging
from datetime import timedelta
from email.mime.base import MIMEBase

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.mail import EmailMessage, send_mail
from django.core.urlresolvers import reverse
from django.utils.crypto import salted_hmac
from django.utils.http import urlquote

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.mail import X_CCIW_ACTION, X_CCIW_CAMP
from cciw.officers.applications import (application_difference, application_rtf_filename, application_to_rtf,
                                        application_to_text, camps_for_application)
from cciw.officers.email_utils import formatted_email, send_mail_with_attachments
from cciw.officers.references import reference_to_text

logger = logging.getLogger(__name__)


X_REFERENCE_REQUEST = 'ReferenceRequest'


def admin_emails_for_camp(camp):
    leaders = ([user for leader in camp.leaders.all()
                for user in leader.users.all()] +
               list(camp.admins.all()))

    return list(filter(lambda x: x is not None,
                       map(formatted_email, leaders)))


def admin_emails_for_application(application):
    """
    For the supplied application, finds the camps admins that are relevant.
    Returns results in groups of (camp, leaders), for each relevant camp.
    """
    camps = camps_for_application(application)
    groups = []
    for camp in camps:
        groups.append((camp, admin_emails_for_camp(camp)))
    return groups


def send_application_emails(request, application):
    if not application.finished:
        return

    # Email to the leaders:

    application_text = application_to_text(application)
    application_rtf = application_to_rtf(application)
    rtf_attachment = (application_rtf_filename(application), application_rtf, 'text/rtf')

    # Collect emails to send to
    leader_email_groups = admin_emails_for_application(application)
    for camp, leader_emails in leader_email_groups:
        # Did the officer submit one last year?
        previous_camp = camp.previous_camp
        application_diff = None
        if previous_camp is not None:
            officer = application.officer
            previous_app = None
            if previous_camp.invitations.filter(officer=officer).exists():
                try:
                    previous_app = officer.applications.filter(date_submitted__lte=previous_camp.start_date,
                                                               date_submitted__gte=previous_camp.start_date + timedelta(-365),
                                                               finished=True)[0]
                except IndexError:
                    pass
            if previous_app is not None:
                application_diff = ("differences_from_last_year.html",
                                    application_difference(previous_app, application),
                                    "text/html")

        if len(leader_emails) > 0:
            send_leader_email(leader_emails, application, application_text, rtf_attachment,
                              application_diff)
        messages.info(request, "The completed application form has been sent to the leaders (%s) via email." %
                      camp.leaders_formatted)

    if len(leader_email_groups) == 0:
        send_leader_email([settings.SECRETARY_EMAIL], application, application_text, rtf_attachment, None)
        messages.info(request,
                      "The application form has been sent to the CCIW secretary, "
                      "because you are not on any camp's officer list this year.")

    # If an admin user corrected an application, we don't send the user a copy
    if request.user == application.officer:
        send_officer_email(application.officer, application, application_text, rtf_attachment)
        messages.info(request, "A copy of the application form has been sent to you via email.")

        if application.officer.email.lower() != application.address_email.lower():
            send_email_change_emails(application.officer, application)


def send_officer_email(officer, application, application_text, rtf_attachment):
    subject = "CCIW application form submitted"

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = ("""%s,

For your records, here is a copy of the application you have submitted
to CCIW. It is also attached to this email as an RTF file.

""" % application.officer.first_name) + application_text

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL,
                                   [user_email], attachments=[rtf_attachment])


def send_leader_email(leader_emails, application, application_text, rtf_attachment,
                      application_diff):
    subject = "CCIW application form from %s" % application.full_name
    body = ("""The following application form has been submitted via the
CCIW website.  It is also attached to this email as an RTF file.

""")
    if application_diff is not None:
        body += ("""The second attachment shows the differences between this year's
application form and last year's - pink indicates information that has
been removed, green indicates new information.

""")

    body += application_text

    attachments = [rtf_attachment]
    if application_diff is not None:
        attachments.append(application_diff)

    send_mail_with_attachments(subject, body, settings.SERVER_EMAIL,
                               leader_emails, attachments=attachments)


def make_update_email_url(application):
    return 'https://%(domain)s%(path)s?t=%(token)s' % dict(
        domain=common.get_current_domain(),
        path=reverse('cciw-officers-correct_email'),
        token=signing.dumps([application.officer.username,
                             application.address_email],
                            salt="cciw-officers-correct_email"))


def make_update_application_url(application, email):
    return 'https://%(domain)s%(path)s?t=%(token)s' % dict(
        domain=common.get_current_domain(),
        path=reverse('cciw-officers-correct_application'),
        token=signing.dumps([application.id,
                             email],
                            salt="cciw-officers-correct_application"))


def send_email_change_emails(officer, application):
    subject = "Email change on CCIW"
    user_email = formatted_email(officer)
    user_msg = ("""%(name)s,

In your most recently submitted application form, you entered your
email address as %(new)s.  The email address stored against your
account is %(old)s.  If you would like this to be updated to '%(new)s'
then click the link below:

 %(correct_email_url)s

If the email address you entered on your application form (%(new)s)
is, in fact, incorrect, then click the link below to correct
your application form to %(old)s:

 %(correct_application_url)s

NB. This email has been sent to both the old and new email
addresses, you only need to respond to one email.

Thanks,


This was an automated response by the CCIW website.


""" % dict(name=officer.first_name, old=officer.email,
           new=application.address_email,
           correct_email_url=make_update_email_url(application),
           correct_application_url=make_update_application_url(application, officer.email),
           )
    )

    send_mail(subject, user_msg, settings.SERVER_EMAIL,
              [user_email, application.address_email], fail_silently=True)


def make_ref_form_url_hash(referee_id, prev_ref_id):
    return salted_hmac("cciw.officers.create_reference_form", "%s:%s" % (referee_id, prev_ref_id)).hexdigest()[::2]


def make_ref_form_url(referee_id, prev_ref_id):
    if prev_ref_id is None:
        prev_ref_id = ""
    return "https://%s%s" % (common.get_current_domain(),
                             reverse('cciw-officers-create_reference_form',
                                     kwargs=dict(referee_id=referee_id,
                                                 prev_ref_id=prev_ref_id,
                                                 hash=make_ref_form_url_hash(referee_id, prev_ref_id))))


def send_reference_request_email(message, referee, sending_officer, camp):
    officer = referee.application.officer
    EmailMessage(subject="Reference for %s %s" % (officer.first_name, officer.last_name),
                 body=message,
                 from_email=settings.REFERENCES_EMAIL,
                 to=[referee.email],
                 headers={'Reply-To': sending_officer.email,
                          X_CCIW_CAMP: camp.slug_name_with_year,
                          X_CCIW_ACTION: X_REFERENCE_REQUEST,
                          }).send()


def send_leaders_reference_email(reference):
    """
    Send the leaders/admins an email with contents of submitted reference form.
    Fails silently.
    """
    referee = reference.referee
    app = referee.application
    officer = app.officer

    refform_text = reference_to_text(reference)
    subject = "CCIW reference form for %s %s from %s" % (officer.first_name, officer.last_name, referee.name)
    body = ("""The following reference form has been submitted via the
CCIW website for officer %s %s.

%s
""" % (officer.first_name, officer.last_name, refform_text)
    )

    leader_email_groups = admin_emails_for_application(app)
    for camp, leader_emails in leader_email_groups:
        send_mail(subject, body, settings.SERVER_EMAIL,
                  leader_emails, fail_silently=False)


def send_nag_by_officer(message, officer, referee, sending_officer):
    EmailMessage(subject="Need reference from %s" % referee.name,
                 body=message,
                 from_email=settings.DEFAULT_FROM_EMAIL,
                 to=[officer.email],
                 headers={'Reply-To': sending_officer.email}).send()


def send_dbs_consent_problem_email(message, officer, camps):
    # If more than one camp involved, we deliberately put all camp leaders
    # together on a single email, so that they can see that more than one camp
    # is involved
    emails = []
    for c in camps:
        emails.extend(admin_emails_for_camp(c))
    send_mail("DBS consent problem for %s %s" % (officer.first_name, officer.last_name),
              message,
              settings.DEFAULT_FROM_EMAIL,
              emails,
              fail_silently=False)


def handle_reference_bounce(bounced_email_address, reply_to, original_message, camp_name):
    admin_emails = [e for name, e in settings.ADMINS]

    if reply_to == '':
        reply_to = admin_emails
    camp = None
    if camp_name is not None:
        try:
            camp_year, camp_slug = camp_name.split("-")
            camp = Camp.objects.get(year=int(camp_year),
                                    camp_name__slug=camp_slug)
        except (ValueError, Camp.DoesNotExist):
            pass

    forward_bounce_to([reply_to], bounced_email_address, original_message, camp)


def forward_with_text(email_addresses, subject, text, original_message):
    rfcmessage = MIMEBase("message", "rfc822")
    rfcmessage.attach(original_message)

    forward = EmailMessage(subject=subject,
                           body=text,
                           from_email=settings.DEFAULT_FROM_EMAIL,
                           to=email_addresses,
                           attachments=[rfcmessage])
    forward.send()


def forward_bounce_to(email_addresses, bounced_email_address, original_message, camp):
    forward_body = """
A reference request (see attached), sent to {email} was not received.

Please find a correct email address for this referee.
""".format(email=bounced_email_address)

    if camp is not None:
        forward_body += """
Use the following link to manage this reference:

{link}
""".format(link="https://www.cciw.co.uk" +
           reverse('cciw-officers-manage_references',
                   kwargs=dict(year=camp.year, slug=camp.slug_name)) +
           "?ref_email=" + urlquote(bounced_email_address))

    forward_with_text(email_addresses,
                      "Reference request to {0} bounced.".format(bounced_email_address),
                      forward_body,
                      original_message)
