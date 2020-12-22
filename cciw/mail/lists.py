# MAILING LIST FUNCTIONALITY

# We provide various group lists e.g. camp-2010-blue-officers@cciw.co.uk and
# other forwarding addresses. This module provides the functionality for
# defining all these addresses (which get registered with AWS SES in the `setup`
# module), and routing incoming mail to them.

import email
import itertools
import logging
import os
import re
import tempfile
from typing import Callable, List

import attr
from django.conf import settings
from django.core.mail import make_msgid, send_mail
from django.utils.encoding import force_bytes

from cciw.accounts.models import (COMMITTEE_ROLE_NAME, DBS_OFFICER_ROLE_NAME, Role, User, get_camp_admin_role_users,
                                  get_role_email_recipients, get_role_users)
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import is_valid_email
from cciw.officers.email_utils import formatted_email
from cciw.officers.models import Application
from cciw.officers.utils import camp_officer_list, camp_slacker_list

from .smtp import send_mime_message

logger = logging.getLogger(__name__)


# Externally used functions:
def find_list(address, from_addr):
    for email_list in get_all_lists():
        if email_list.matches(address, from_addr):
            return email_list
    raise NoSuchList()


def get_all_lists():
    current_camps = Camp.objects.all().filter(year__gte=common.get_thisyear() - 1)
    for generator in GENERATORS:
        for email_list in generator(current_camps):
            yield email_list


def address_for_camp_officers(camp):
    return make_camp_officers_list(camp).address


def address_for_camp_slackers(camp):
    return make_camp_slackers_list(camp).address


def address_for_camp_leaders(camp):
    return make_camp_leaders_list(camp).address


# Reading mailboxes
email_extract_re = re.compile(r"([a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)", re.IGNORECASE)


def extract_email_addresses(email_line):
    return email_extract_re.findall(email_line)


class NoSuchList(ValueError):
    pass


class MailAccessDenied(ValueError):
    pass


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


@attr.s(auto_attribs=True)
class EmailList(object):
    local_address: str
    get_members: Callable[[], List[User]]
    has_permission: Callable[[], bool]
    list_reply: bool

    @property
    def address(self):
        return self.local_address + '@' + self.domain

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


# Definitions of EmailLists

def camp_officers_list_generator(current_camps):
    for camp in current_camps:
        yield make_camp_officers_list(camp)


def make_camp_officers_list(camp):
    def get_members():
        return camp_officer_list(camp)

    def has_permission(email_address):
        return is_camp_leader_or_admin(email_address, [camp])

    return EmailList(
        local_address=f'camp-{camp.url_id}-officers',
        get_members=get_members,
        has_permission=has_permission,
        list_reply=False,
    )


def camp_slackers_list_generator(current_camps):
    for camp in current_camps:
        yield make_camp_slackers_list(camp)


def make_camp_slackers_list(camp):
    def get_members():
        return camp_slacker_list(camp)

    def has_permission(email_address):
        return is_camp_leader_or_admin(email_address, [camp])

    return EmailList(
        local_address=f'camp-{camp.url_id}-slackers',
        get_members=get_members,
        has_permission=has_permission,
        list_reply=False,
    )


def camp_leaders_list_generator(current_camps):
    for camp in current_camps:
        yield make_camp_leaders_list(camp)


def make_camp_leaders_list(camp):
    def get_members():
        return get_leaders_for_camp(camp)

    def has_permission(email_address):
        return is_camp_leader_or_admin_or_dbs_officer_or_superuser(email_address, [camp])

    return EmailList(
        local_address=f'camp-{camp.url_id}-leaders',
        get_members=get_members,
        has_permission=has_permission,
        list_reply=False,
    )


def camp_leaders_for_year_list_generator(current_camps):
    get_year = lambda camp: camp.year
    for year, camps in itertools.groupby(sorted(current_camps, key=get_year), key=get_year):
        camps = list(camps)
        yield make_camp_leaders_for_year_list(year, camps)


def make_camp_leaders_for_year_list(year, camps):
    def get_members():
        s = set()
        for c in camps:
            s.update(get_leaders_for_camp(c))
        return sorted(list(s))

    def has_permission(email_address):
        return is_camp_leader_or_admin_or_dbs_officer_or_superuser(email_address, camps)

    return EmailList(
        local_address=f'camps-{year}-leaders',
        get_members=get_members,
        has_permission=has_permission,
        list_reply=True,
    )


def debug_list_generator(current_camps):
    return [EmailList(
        local_address='camp-debug',
        get_members=get_webmasters,
        has_permission=lambda email_address: True,
        list_reply=True,
    )]


def webmaster_list_generator(current_camps):
    return [EmailList(
        local_address='webmaster',
        get_members=get_webmasters,
        has_permission=lambda email_address: True,
        list_reply=False,
    )]


def roles_list_generator(current_camps):
    for role in Role.objects.with_address():
        local_address, domain = role.email.rsplit('@', 1)
        if domain != settings.INCOMING_MAIL_DOMAIN:
            continue

        def has_permission(email_address, role=role):
            if role.allow_emails_from_public:
                return True
            else:
                return get_role_email_recipients(COMMITTEE_ROLE_NAME).filter(email__iexact=email_address).exists() or is_superuser(email_address)

        yield EmailList(
            local_address=local_address,
            get_members=lambda role=role: role.email_recipients.all(),
            has_permission=has_permission,
            list_reply=not role.allow_emails_from_public
        )


GENERATORS = [
    camp_officers_list_generator,
    camp_slackers_list_generator,
    camp_leaders_list_generator,
    camp_leaders_for_year_list_generator,
    debug_list_generator,
    webmaster_list_generator,
    roles_list_generator,
]


# Helper functions for lists:

def get_webmasters():
    return User.objects.filter(is_superuser=True)


def get_leaders_for_camp(camp):
    retval = set()
    for p in camp.leaders.all().prefetch_related('users'):
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


def is_camp_leader_or_admin_or_dbs_officer_or_superuser(email_address, camps):
    if is_camp_leader_or_admin(email_address, camps):
        return True

    if email_match(email_address, get_camp_admin_role_users()):
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
    # Unlike mail[header], this removes existing values. This can be important
    # when duplicate headers are not allowed (and this can cause email sending
    # to fail)
    if header in mail:
        del mail[header]
    mail[header] = value


def forward_email_to_list(mail, email_list: EmailList):
    orig_from_addr = mail['From']
    reply_to = mail.get('Reply-To', orig_from_addr)
    if email_list.list_reply:
        _set_mail_header(mail, 'Sender', email_list.address)
        _set_mail_header(mail, 'List-Post', f'<mailto:{email_list.address}>')
    else:
        _set_mail_header(mail, 'Sender', settings.SERVER_EMAIL)
    _set_mail_header(mail, 'From', mangle_from_address(orig_from_addr))
    _set_mail_header(mail, 'X-Original-From', orig_from_addr)
    _set_mail_header(mail, 'Return-Path', settings.SERVER_EMAIL)
    _set_mail_header(mail, 'Reply-To', reply_to)

    # Various headers seem to cause problems. We whitelist the ones
    # that are OK:
    good_headers = [
        'content-type',
        'content-transfer-encoding',
        'subject',
        'from',
        'mime-version',
        'user-agent',
        'content-disposition',
        'date',
        'reply-to',
        'sender',
        'list-post',
        'x-original-from',
        'disposition-notification-to',
        'return-receipt-to',
    ]
    mail._headers = [(name, val) for name, val in mail._headers
                     if name.lower() in good_headers]

    # send individual emails.

    # First, do as much work as possible before doing anything
    # with side effects. That way if an error occurs early,
    # we reduce the possibility of having sent some of the emails
    # but not others.

    messages_to_send = []
    for user in email_list.get_members():
        addr = formatted_email(user)
        _set_mail_header(mail, 'To', addr)
        # Need new message ID, or some mail servers will only send one
        _set_mail_header(mail, 'Message-ID', make_msgid())
        mail_as_bytes = force_bytes(mail.as_string())
        from_address = mail['From']
        messages_to_send.append(
            (addr, from_address, mail_as_bytes)
        )

    if len(messages_to_send) == 0:
        return

    errors = []
    for to_addr, from_address, mail_as_bytes in messages_to_send:
        try:
            send_mime_message(to_addr, from_address, mail_as_bytes)
        except Exception as e:
            errors.append((addr, e))

    if len(errors) == len(messages_to_send):
        # Probably a temporary network error, but possibly something more
        # serious, and maybe email is down completely. In that case, there is no
        # point trying to notify by email (as below). Instead we re-raise the
        # last error, which will send errors to Sentry, which hopefully should
        # notify us.
        raise errors[-1][1]

    if errors:
        # Attempt to report problem
        address_messages = [
            f"{address}: {str(e)}"
            for address, e in errors
        ]
        msg = """
You attempted to email the list {0}
with an email title "{1}".

There were problems with the following addresses:

{2}
""".format(email_list.address, mail['Subject'], '\n'.join(address_messages))
        send_mail(f"[CCIW] Error with email to list {email_list.address}",
                  msg,
                  settings.DEFAULT_FROM_EMAIL,
                  [orig_from_addr],
                  fail_silently=True)


def mangle_from_address(address):
    address = address.replace("@", "(at)").replace("<", "").replace(">", "")
    address = address + " via <noreply@cciw.co.uk>"
    return address


INCOMING_MAIL_TEMPFILE_PREFIX = "mail-incoming-"


def handle_mail_async(data):
    fd, name = tempfile.mkstemp(prefix=INCOMING_MAIL_TEMPFILE_PREFIX)
    os.write(fd, data)
    os.close(fd)
    manage_py_path = os.path.join(settings.PROJECT_ROOT, "manage.py")
    os.spawnlp(os.P_NOWAIT, "nohup", "nohup", manage_py_path, "handle_message", name)


def handle_mail(data):
    """
    Forwards an email to the correct list of people.
    data is RFC822 formatted bytes
    """
    mail = email.message_from_bytes(data)
    to = mail['To']
    assert to is not None, "Message did not have 'To' field set, cannot send email"

    if is_valid_email(to):
        addresses = [to]
    else:
        addresses = set([a.lower() for a in extract_email_addresses(to)])

    if mail.get('X-SES-Spam-Verdict', '') == 'FAIL':
        logger.info('Discarding spam, message-id %s', mail.get('Message-ID', '<unknown>'))
        return
    if mail.get('X-SES-Virus-Verdict', '') == 'FAIL':
        logger.info('Discarding virus, message-id %s', mail.get('Message-ID', '<unknown>'))
        return

    from_email = extract_email_addresses(mail['From'])[0]

    for address in addresses:
        try:
            email_list = find_list(address, from_email)
            forward_email_to_list(mail, email_list)
        except MailAccessDenied:
            if not known_officer_email_address(from_email):
                # Don't bother sending bounce emails to addresses
                # we've never seen before. This is highly likely to be spam.
                continue
            send_mail(
                f"[CCIW] Access to mailing list {address} denied",
                f"You attempted to email the list {address}\n"
                f"with an email titled \"{mail['Subject']}\".\n"
                f"\n"
                f"However, you do not have permission to email this list, \n"
                f"or the list does not exist. Sorry!",
                settings.DEFAULT_FROM_EMAIL,
                [from_email],
                fail_silently=True)
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
