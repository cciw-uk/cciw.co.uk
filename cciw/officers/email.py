import contextlib
import logging
from email.mime.base import MIMEBase
from urllib.parse import quote as urlquote

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.mail import EmailMessage, send_mail
from django.urls import reverse
from django.utils.crypto import salted_hmac

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.mail import X_CCIW_ACTION, X_CCIW_CAMP
from cciw.officers.applications import (
    application_rtf_filename,
    application_to_rtf,
    application_to_text,
    camps_for_application,
)
from cciw.officers.email_utils import formatted_email, send_mail_with_attachments

logger = logging.getLogger(__name__)


X_REFERENCE_REQUEST = "ReferenceRequest"


def admin_emails_for_camp(camp):
    leaders = [user for leader in camp.leaders.all() for user in leader.users.all()] + list(camp.admins.all())

    return list(filter(lambda x: x is not None, map(formatted_email, leaders)))


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

    # Collect emails to send to
    leader_email_groups = admin_emails_for_application(application)
    for camp, leader_emails in leader_email_groups:

        if len(leader_emails) > 0:
            send_leader_email(leader_emails, application)
        messages.info(
            request,
            f"The leaders ({camp.leaders_formatted}) have been notified of the completed application form by email.",
        )

    if len(leader_email_groups) == 0:
        send_leader_email(settings.SECRETARY_EMAILS, application)
        messages.info(
            request,
            "The application form has been sent to the CCiW secretary, "
            "because you are not on any camp's officer list this year.",
        )

    # If this is someone editing their own application, we send them a copy, but
    # not otherwise.
    if request.user == application.officer:
        application_text = application_to_text(application)
        application_rtf = application_to_rtf(application)
        rtf_attachment = (application_rtf_filename(application), application_rtf, "text/rtf")

        send_officer_email(application.officer, application, application_text, rtf_attachment)
        messages.info(request, "A copy of the application form has been sent to you via email.")

        if application.officer.email.lower() != application.address_email.lower():
            send_email_change_emails(application.officer, application)


def send_officer_email(officer, application, application_text, rtf_attachment):
    subject = "[CCIW] Application form submitted"

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = (
        (
            f"""{application.officer.first_name},

For your records, here is a copy of the application you have submitted
to CCiW. It is also attached to this email as an RTF file.

"""
        )
        + application_text
    )

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL, [user_email], attachments=[rtf_attachment])


def send_leader_email(leader_emails, application):
    subject = f"[CCIW] Application form from {application.full_name}"
    url = "https://{domain}{path}".format(
        domain=common.get_current_domain(),
        path=reverse("cciw-officers-view_application", kwargs=dict(application_id=application.id)),
    )
    body = f"""The following application form has been submitted via the
CCiW website:

{url}

"""

    send_mail(subject, body, settings.SERVER_EMAIL, leader_emails)


def make_update_email_url(application):
    return "https://{domain}{path}?t={token}".format(
        domain=common.get_current_domain(),
        path=reverse("cciw-officers-correct_email"),
        token=signing.dumps(
            [application.officer.username, application.address_email], salt="cciw-officers-correct_email"
        ),
    )


def make_update_application_url(application, email):
    return "https://{domain}{path}?t={token}".format(
        domain=common.get_current_domain(),
        path=reverse("cciw-officers-correct_application"),
        token=signing.dumps([application.id, email], salt="cciw-officers-correct_application"),
    )


def send_email_change_emails(officer, application):
    subject = "[CCIW] Email change on CCiW"
    user_email = formatted_email(officer)
    user_msg = """{name},

In your most recently submitted application form, you entered your
email address as {new}.  The email address stored against your
account is {old}.  If you would like this to be updated to '{new}'
then click the link below:

 {correct_email_url}

If the email address you entered on your application form ({new})
is, in fact, incorrect, then click the link below to correct
your application form to {old}:

 {correct_application_url}

NB. This email has been sent to both the old and new email
addresses, you only need to respond to one email.

Thanks,


This was an automated response by the CCiW website.


""".format(
        name=officer.first_name,
        old=officer.email,
        new=application.address_email,
        correct_email_url=make_update_email_url(application),
        correct_application_url=make_update_application_url(application, officer.email),
    )

    send_mail(subject, user_msg, settings.SERVER_EMAIL, [user_email, application.address_email], fail_silently=True)


def make_ref_form_url_hash(referee_id, prev_ref_id):
    return salted_hmac("cciw.officers.create_reference", f"{referee_id}:{prev_ref_id}").hexdigest()[::2]


def make_ref_form_url(referee_id, prev_ref_id):
    if prev_ref_id is None:
        prev_ref_id = ""
    return "https://{domain}{path}".format(
        domain=common.get_current_domain(),
        path=reverse(
            "cciw-officers-create_reference",
            kwargs=dict(
                referee_id=referee_id, prev_ref_id=prev_ref_id, hash=make_ref_form_url_hash(referee_id, prev_ref_id)
            ),
        ),
    )


def send_reference_request_email(message, referee, sending_officer, camp):
    officer = referee.application.officer
    EmailMessage(
        subject=f"[CCIW] Reference for {officer.full_name}",
        body=message,
        from_email=settings.WEBMASTER_FROM_EMAIL,
        to=[referee.email],
        headers={
            "Reply-To": sending_officer.email,
            X_CCIW_CAMP: str(camp.url_id),
            X_CCIW_ACTION: X_REFERENCE_REQUEST,
        },
    ).send()


def send_leaders_reference_email(reference):
    """
    Send the leaders/admins an email with contents of submitted reference form.
    Fails silently.
    """
    referee = reference.referee
    app = referee.application
    officer = app.officer

    view_reference_url = "https://{domain}{path}".format(
        domain=common.get_current_domain(),
        path=reverse("cciw-officers-view_reference", kwargs=dict(reference_id=reference.id)),
    )
    subject = f"[CCIW] Reference form for {officer.full_name} from {referee.name}"
    body = f"""The following reference form has been submitted via the
CCiW website for officer {officer.full_name}.

{view_reference_url}
"""

    leader_email_groups = admin_emails_for_application(app)
    for camp, leader_emails in leader_email_groups:
        send_mail(subject, body, settings.SERVER_EMAIL, leader_emails, fail_silently=False)


def send_nag_by_officer(message, officer, referee, sending_officer):
    EmailMessage(
        subject=f"[CCIW] Need reference from {referee.name}",
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[officer.email],
        headers={"Reply-To": sending_officer.email},
    ).send()


def send_dbs_consent_alert_leaders_email(message, officer, camps):
    # If more than one camp involved, we deliberately put all camp leaders
    # together on a single email, so that they can see that more than one camp
    # is involved
    emails = []
    for c in camps:
        emails.extend(admin_emails_for_camp(c))
    if emails:
        send_mail(
            f"[CCIW] DBS consent problem for {officer.full_name}",
            message,
            settings.DEFAULT_FROM_EMAIL,
            emails,
            fail_silently=False,
        )


def send_request_for_dbs_form_email(message, officer, sending_officer):
    EmailMessage(
        subject=f"[CCIW] DBS form needed for {officer.full_name}",
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.EXTERNAL_DBS_OFFICER["email"]],
        headers={"Reply-To": sending_officer.email},
    ).send()


def handle_reference_bounce(bounced_email_address, reply_to, original_message, camp_name):
    admin_emails = [e for name, e in settings.ADMINS]

    if reply_to == "":
        reply_to = admin_emails
    camp = None
    if camp_name is not None:
        with contextlib.suppress(ValueError, Camp.DoesNotExist):
            camp_year, camp_slug = camp_name.split("-")
            camp = Camp.objects.get(year=int(camp_year), camp_name__slug=camp_slug)
    forward_bounce_to([reply_to], bounced_email_address, original_message, camp)


def forward_with_text(email_addresses, subject, text, original_message):
    if original_message is not None:
        rfcmessage = MIMEBase("message", "rfc822")
        rfcmessage.attach(original_message)
        attachments = [rfcmessage]
    else:
        attachments = None

    forward = EmailMessage(
        subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=email_addresses, attachments=attachments
    )
    forward.send()


def forward_bounce_to(email_addresses, bounced_email_address, original_message, camp):
    forward_body = f"""
A reference request (see attached), sent to {bounced_email_address} was not received.

Please find a correct email address for this referee.
"""

    if camp is not None:
        forward_body += """
Use the following link to manage this reference:

{link}
""".format(
            link="https://"
            + common.get_current_domain()
            + reverse("cciw-officers-manage_references", kwargs=dict(camp_id=camp.url_id))
            + "?ref_email="
            + urlquote(bounced_email_address)
        )

    logger.info(
        "Sending 'Reference request bounced' for email %s to addresses %s", bounced_email_address, email_addresses
    )
    forward_with_text(
        email_addresses, f"[CCIW] Reference request to {bounced_email_address} bounced.", forward_body, original_message
    )
