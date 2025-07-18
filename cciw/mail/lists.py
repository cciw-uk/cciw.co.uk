# MAILING LIST FUNCTIONALITY

# We provide various group lists e.g. camp-2010-blue-officers@cciw.co.uk and
# other forwarding addresses. This module provides the functionality for
# defining all these addresses (which get registered with AWS SES in the `setup`
# module), and routing incoming mail to them.

import email
import email.policy
import fcntl
import itertools
import logging
import os
import re
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import make_msgid, send_mail
from django.utils.encoding import force_bytes

from cciw.accounts.models import (
    DBS_OFFICER_ROLE_NAME,
    Role,
    User,
    get_camp_manager_role_users,
    get_role_email_recipients,
    get_role_users,
)
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import is_valid_email
from cciw.officers.email_utils import formatted_email
from cciw.officers.models import Application
from cciw.officers.utils import camp_officer_list, camp_slacker_list

from .ses import download_ses_message_from_s3
from .smtp import send_mime_message

logger = logging.getLogger(__name__)


# We have:

# EmailList
#  - essentially a list of people to email
#
#  - with an address i.e. the email address of the group. This is used for
#    setting up 'routing' in our email provider.
#
#  - with methods to check whether an incoming email matches the list and can
#    send to it.
#
# generators:
#
# - A callable object that will generate a sequence of EmailList objects. It is
#   needed because the groups that exist depend on an unknown number of records
#   from the DB.
#
#   We pass 'current_camps' into these generators as an optimization to
#   stop them having to do lots of the same DB queries over and over.


@dataclass
class EmailList:
    local_address: str
    get_members: Callable[[], Iterable[User]]
    has_permission: Callable[[str], bool]
    list_reply: bool

    @property
    def address(self):
        return self.local_address + "@" + self.domain

    @property
    def domain(self):
        return settings.INCOMING_MAIL_DOMAIN

    def matches(self, address, from_address):
        """
        Returns a True if `address` matches
        this group list, and the `from_address` matches
        an allowed sender.

        If the from_address doesn't have permission,
        raises MailAccessDenied

        Otherwise if no match, returns False
        """
        if address != self.address:
            return False
        if not self.has_permission(from_address):
            raise MailAccessDenied()
        return True


# Externally used functions:
def find_list(address, from_addr) -> EmailList:
    for email_list in get_all_lists():
        if email_list.matches(address, from_addr):
            return email_list
    raise NoSuchList()


def get_all_lists() -> Iterable[EmailList]:
    current_camps = Camp.objects.all().filter(year__gte=common.get_thisyear() - 1)
    for generator in GENERATORS:
        yield from generator(current_camps)


def address_for_camp_officers(camp: Camp) -> str:
    return make_camp_officers_list(camp).address


def address_for_camp_slackers(camp: Camp) -> str:
    return make_camp_slackers_list(camp).address


def address_for_camp_leaders(camp: Camp) -> str:
    return make_camp_leaders_list(camp).address


# Reading mailboxes
email_extract_re = re.compile(
    r"([a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)",
    re.IGNORECASE,
)


def extract_email_addresses(email_line: str) -> list[str]:
    return email_extract_re.findall(email_line)


class NoSuchList(ValueError):
    pass


class MailAccessDenied(ValueError):
    pass


# Definitions of EmailLists


def camp_officers_list_generator(current_camps: Sequence[Camp]) -> Iterable[EmailList]:
    for camp in current_camps:
        yield make_camp_officers_list(camp)


def make_camp_officers_list(camp: Camp) -> EmailList:
    def get_members() -> list[User]:
        return camp_officer_list(camp)

    def has_permission(email_address):
        return is_camp_leader_or_admin(email_address, [camp])

    return EmailList(
        local_address=f"camp-{camp.url_id}-officers",
        get_members=get_members,
        has_permission=has_permission,
        list_reply=False,
    )


def camp_slackers_list_generator(current_camps: Sequence[Camp]) -> Iterable[EmailList]:
    for camp in current_camps:
        yield make_camp_slackers_list(camp)


def make_camp_slackers_list(camp):
    def get_members() -> list[User]:
        return camp_slacker_list(camp)

    def has_permission(email_address):
        return is_camp_leader_or_admin(email_address, [camp])

    return EmailList(
        local_address=f"camp-{camp.url_id}-slackers",
        get_members=get_members,
        has_permission=has_permission,
        list_reply=False,
    )


def camp_leaders_list_generator(current_camps: Sequence[Camp]) -> Iterable[EmailList]:
    for camp in current_camps:
        yield make_camp_leaders_list(camp)


def make_camp_leaders_list(camp):
    def get_members() -> set[User]:
        return get_leaders_for_camp(camp)

    def has_permission(email_address):
        return is_camp_admin_or_manager_or_dbs_officer_or_superuser(email_address, [camp])

    return EmailList(
        local_address=f"camp-{camp.url_id}-leaders",
        get_members=get_members,
        has_permission=has_permission,
        list_reply=False,
    )


def camp_leaders_for_year_list_generator(current_camps: Sequence[Camp]) -> Iterable[EmailList]:
    get_year = lambda camp: camp.year
    for year, camps in itertools.groupby(sorted(current_camps, key=get_year), key=get_year):
        camps2 = list(camps)
        yield make_camp_leaders_for_year_list(year, camps2)


def make_camp_leaders_for_year_list(year, camps) -> EmailList:
    def get_members() -> list[User]:
        s = set()
        for c in camps:
            s.update(get_leaders_for_camp(c))
        return sorted(list(s), key=lambda user: user.email)

    def has_permission(email_address):
        return is_camp_admin_or_manager_or_dbs_officer_or_superuser(email_address, camps)

    return EmailList(
        local_address=f"camps-{year}-leaders",
        get_members=get_members,
        has_permission=has_permission,
        list_reply=True,
    )


def roles_list_generator(current_camps: Sequence[Camp]) -> Iterable[EmailList]:
    for role in Role.objects.with_address():
        local_address, domain = role.email.rsplit("@", 1)
        if domain != settings.INCOMING_MAIL_DOMAIN:
            continue

        def has_permission(email_address, role=role):
            if role.allow_emails_from_public:
                return True
            else:
                return get_role_email_recipients(role.name).filter(
                    email__iexact=email_address
                ).exists() or is_superuser(email_address)

        yield EmailList(
            local_address=local_address,
            get_members=lambda role=role: role.email_recipients.all(),
            has_permission=has_permission,
            list_reply=not role.allow_emails_from_public,
        )


type Generator = Callable[[Sequence[Camp]], Iterable[EmailList]]

GENERATORS: list[Generator] = [
    camp_officers_list_generator,
    camp_slackers_list_generator,
    camp_leaders_list_generator,
    camp_leaders_for_year_list_generator,
    roles_list_generator,
]


# Helper functions for lists:


def get_leaders_for_camp(camp) -> set[User]:
    retval = set()
    for p in camp.leaders.all().prefetch_related("users"):
        for u in p.users.all():
            retval.add(u)
    return retval


def email_match(email_address, users):
    return any(user.email.lower() == email_address.lower() for user in users)


def is_camp_leader_or_admin(email_address, camps):
    all_users = set()
    for camp in camps:
        all_users.update(get_leaders_for_camp(camp))
        all_users.update(list(camp.admins.all()))
    return email_match(email_address, all_users)


def is_camp_admin_or_manager_or_dbs_officer_or_superuser(email_address, camps):
    if is_camp_leader_or_admin(email_address, camps):
        return True

    if email_match(email_address, get_camp_manager_role_users()):
        return True

    if get_role_users(DBS_OFFICER_ROLE_NAME).filter(email__iexact=email_address).exists():
        return True

    if is_superuser(email_address):
        return True

    return False


def is_superuser(email_address):
    return User.objects.filter(email__iexact=email_address, is_superuser=True).exists()


# Handling incoming mail


def _set_mail_header(mail, header, value):
    """
    Overwrite a header in the email
    """
    # If you do `mail[header] = value`, you get a new $header header, without
    # removing the old one if it existed. In many cases this can cause
    # sending to fail, because duplicates are not allowed or don't make sense.
    # This function by constrast ensures we first remove the header.
    # to fail)
    if header in mail:
        del mail[header]
    mail[header] = value


def forward_email_to_list(mail, email_list: EmailList):
    orig_from_addr = mail["From"]
    orig_msg_id = mail.get("Message-ID", "unknown")
    # Use 'reply-to' header for reply-to, if it exists, falling back to 'From'
    reply_to = mail.get("Reply-To", orig_from_addr)
    if email_list.list_reply:
        _set_mail_header(mail, "Sender", email_list.address)
        _set_mail_header(mail, "List-Post", f"<mailto:{email_list.address}>")
    else:
        _set_mail_header(mail, "Sender", settings.SERVER_EMAIL)

    # If we leave 'From' as it is, e.g bob@example.com, we will be sending out a
    # new email on behalf of bob@example.com. At some point in the chain of processing
    # that follows, an email server will:
    # - look up DKIM/SPF info about @example.com
    # - realize that our email server is not a legitimate email server
    #   for @example.com
    # - conclude that this email is spam and bin it.
    #
    # This is all working as designed, and you can't work around it (unless you
    # are a huge tech giant, like Google Groups and probably some others).
    #
    # So, we can't claim that this email is 'From' bob@example.com,
    # and we instead put an `@cciw.co.uk` address in there, but
    # with a mangled form of bob@example.com visible.
    _set_mail_header(mail, "From", mangle_from_address(orig_from_addr))
    # But we can set this debugging header to preserve the info:
    _set_mail_header(mail, "X-Original-From", orig_from_addr)
    # Return-Path: indicates how bounces should be handled
    _set_mail_header(mail, "Return-Path", settings.SERVER_EMAIL)
    _set_mail_header(mail, "Reply-To", reply_to)
    _set_mail_header(mail, "X-Original-To", email_list.address)

    # Various headers seem to cause problems. We whitelist the ones
    # that are OK:
    good_headers = [
        "content-type",
        "content-transfer-encoding",
        "subject",
        "from",
        "mime-version",
        "user-agent",
        "content-disposition",
        "date",
        "reply-to",
        "sender",
        "list-post",
        "x-original-from",
        "disposition-notification-to",
        "return-receipt-to",
        "return-path",
        "x-original-to",
    ]
    mail._headers = [(name, val) for name, val in mail._headers if name.lower() in good_headers]

    # Send individual or group emails:

    # First, do as much work as possible before doing anything
    # with side effects. That way if an error occurs early,
    # we reduce the possibility of having sent some of the emails
    # but not others.

    user_groups_for_sending: list[list[User]]

    if email_list.list_reply:
        # Because some email clients don't have 'Reply to List'
        # or people don't know how to use it, we make each user
        # an explicit recipient on the same email.
        user_groups_for_sending = [list(email_list.get_members())]
    else:
        # Give each recipient their own email.
        user_groups_for_sending = [[user] for user in email_list.get_members()]

    messages_to_send: list[tuple[list[str], str, bytes]] = []
    for group in user_groups_for_sending:
        to_addresses = [addr for user in group if (addr := formatted_email(user)) is not None]
        if not to_addresses:
            continue
        _set_mail_header(mail, "To", ",".join(to_addresses))

        # Need new message ID, or some mail servers will only send one
        _set_mail_header(mail, "Message-ID", make_msgid())
        try:
            mail_as_bytes = force_bytes(mail.as_string())
        except UnicodeEncodeError:
            # Can happen for bad mail, usually spammers
            continue
        from_address = mail["From"]
        messages_to_send.append((to_addresses, from_address, mail_as_bytes))

    if len(messages_to_send) == 0:
        return

    errors = []
    for to_addresses, from_address, mail_as_bytes in messages_to_send:
        try:
            logger.info(
                "Forwarding msg %s from %s to email list %s address %s",
                orig_msg_id,
                orig_from_addr,
                email_list.address,
                to_addresses,
            )
            send_mime_message(to_addresses, from_address, mail_as_bytes)
        except Exception as e:
            errors.append((to_addresses, e))

    if len(errors) == len(messages_to_send):
        # Probably a temporary network error, but possibly something more
        # serious, and maybe email is down completely. In that case, there is no
        # point trying to notify by email (as below). Instead we re-raise the
        # last error, which will send errors to Sentry, which hopefully should
        # notify us.
        raise errors[-1][1]

    if errors:
        # Attempt to report problem
        address_messages = [f"{address}: {str(e)}" for address, e in errors]
        subject = mail["Subject"]
        msg = f"""
You attempted to email the list {email_list.address}
with an email titled "{subject}".

There were problems with the following addresses:

{'\n'.join(address_messages)}
"""
        send_mail(
            f"[CCIW] Error with email to list {email_list.address}",
            msg,
            settings.DEFAULT_FROM_EMAIL,
            [orig_from_addr],
            fail_silently=True,
        )


def mangle_from_address(address):
    address = address.replace("@", "(at)").replace("<", "").replace(">", "").replace('"', "")
    address = f'"{address}" <noreply@cciw.co.uk>'
    return address


INCOMING_MAIL_TEMPFILE_PREFIX = "mail-incoming-"


def handle_mail_from_s3_async(message_id):
    manage_py_path = os.path.join(settings.PROJECT_ROOT, "manage.py")
    # Poor man's async - use spawnlp which returns instantly.
    # Indirectly calls handle_mail_from_s3 below.
    os.spawnlp(os.P_NOWAIT, "nohup", "nohup", manage_py_path, "handle_message", message_id)


def handle_mail_from_s3(message_id: str):
    # There is the possibility of this getting called multiple times with the
    # same message_id, perhaps due to our endpoint not returning quickly enough
    # to SNS, triggering a timeout and re-attempt. So, we dedupe using a
    # filesystem based lock.

    filename = tempfile.gettempdir() + "/" + INCOMING_MAIL_TEMPFILE_PREFIX + message_id
    if os.path.exists(filename):
        logger.info("Aborting mail handling, file %s already exists", filename)
        return

    # We have a potential race condition between checking for the file existing
    # above, and opening it below. So after opening it we do a lock as well.
    with open(filename, "wb") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info("Aborting mail handling, lock on file %s already exists", filename)
            return

        data = download_ses_message_from_s3(message_id)
        # We don't technically need to write the data here, but it helps
        # debugging later.
        f.write(data)
        handle_mail(data)

    # We leave the file behind (to be cleaned by a cron job), so that later
    # calls with the same message_id will see the file already exists and abort.


def handle_mail(data: bytes):
    """
    Forwards an email to the correct list of people.
    data is RFC822 formatted bytes
    """
    mail = email.message_from_bytes(data, policy=email.policy.SMTP)
    to = mail["To"]
    if to is None:
        # Some spam is like this.
        return

    if is_valid_email(to):
        addresses = {to}
    else:
        addresses = {a.lower() for a in extract_email_addresses(to)}

    if mail.get("X-SES-Spam-Verdict", "") == "FAIL":
        logger.info("Discarding spam, message-id %s", mail.get("Message-ID", "<unknown>"))
        return
    if mail.get("X-SES-Virus-Verdict", "") == "FAIL":
        logger.info("Discarding virus, message-id %s", mail.get("Message-ID", "<unknown>"))
        return

    from_header = mail["From"]
    if not isinstance(from_header, str):
        # Sometimes get Header instance here. So far it has only happened with spam mail
        # which seems to be malformed (unicode chars in a header instead of "encoded word" syntax)
        logger.info("Discarding malformed mail, message-id %s", mail.get("Message-ID", "<unknown>"))
        return

    try:
        from_email = extract_email_addresses(from_header)[0]
    except IndexError:
        logger.info(
            "Discarding mail with no email address in From header, message-id %s", mail.get("Message-ID", "<unknown>")
        )
        return

    for address in sorted(list(addresses)):
        try:
            email_list = find_list(address, from_email)
            forward_email_to_list(mail, email_list)
        except MailAccessDenied:
            if not known_officer_email_address(from_email):
                # Don't bother sending bounce emails to addresses
                # we've never seen before. This is highly likely to be spam.
                logger.info("Ignoring mail to %s from unknown email %s", address, from_email)
                continue
            subject = mail["Subject"]
            logger.info("Access denied to %s from known email %s, sending rejection email", address, from_email)
            send_mail(
                f"[CCIW] Access to mailing list {address} denied",
                f"You attempted to email the list {address}\n"
                f'with an email titled "{subject}".\n'
                f"\n"
                f"However, you do not have permission to email this list, \n"
                f"or the list does not exist. Sorry!",
                settings.DEFAULT_FROM_EMAIL,
                [from_email],
                fail_silently=True,
            )
        except NoSuchList:
            # addresses can contain anything else on the 'to' line, which
            # can even included valid @cciw.co.uk that we don't know about
            # (e.g. other mailboxes).  So if we don't recognise the
            # address, just ignore. In practice, AWS should bounce these
            # for us because we only have routes created for the email
            # we expect.
            pass


def known_officer_email_address(address):
    if User.objects.filter(email__iexact=address).exists():
        return True
    if Application.objects.filter(address_email__iexact=address).exists():
        return True
    return False
