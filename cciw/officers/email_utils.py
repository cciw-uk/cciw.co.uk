"""
Utilities for sending email with attachments
"""

from django.core.mail import EmailMessage, get_connection
from django.utils.safestring import SafeString

from cciw.accounts.models import User


def send_mail_with_attachments(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: list[str],
    *,
    fail_silently: bool = False,
    auth_user: None = None,
    auth_password: None = None,
    attachments: list[tuple[str, SafeString, str]] | None = None,
) -> int:
    connection = get_connection(username=auth_user, password=auth_password, fail_silently=fail_silently)
    return EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
        connection=connection,
        attachments=attachments,
    ).send()


def formatted_email(user: User) -> str | None:
    """
    Get the email address plus name of the user, formatted for
    use in sending an email, or 'None' if no email address available
    """
    name = user.full_name.strip().replace('"', "")
    email = user.email.strip()
    if len(email) == 0:
        return None
    elif len(name) > 0:
        return f'"{name}" <{email}>'
    else:
        return email
