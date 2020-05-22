# MAILING LIST FUNCTIONALITY

# It would be possible to use Mailgun's "Mailing list" functionality for this.
# However, keeping the lists up to date would be tricky - they can change whenever:
#
# * officer email addresses are changed, including 'update()' methods which don't
#   generate 'post_save' signals
# * application forms are received
# * officers are added/removed from camp invitation lists
# * camps are created
# * probably other events...
#
# So it is easier to redirect mail to the website and do the mailing list
# functionality ourselves.


import email
import os
import re
import tempfile

import attr
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import make_msgid, send_mail
from django.utils.encoding import force_bytes

from cciw.accounts.models import (COMMITTEE_GROUP_NAME, DBS_OFFICER_GROUP_NAME, get_camp_admin_group_users,
                                  get_group_users)
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import is_valid_email
from cciw.officers.email_utils import formatted_email
from cciw.officers.models import Application
from cciw.officers.utils import camp_officer_list, camp_slacker_list

from .smtp import send_mime_message

# External utility functions #


# See also below for changes to format
def address_for_camp_officers(camp):
    return f"camp-{camp.url_id}-officers@cciw.co.uk"


def address_for_camp_slackers(camp):
    return f"camp-{camp.url_id}-slackers@cciw.co.uk"


def address_for_camp_leaders(camp):
    return f"camp-{camp.url_id}-leaders@cciw.co.uk"


def address_for_camp_leaders_year(year):
    return "camps-%d-leaders@cciw.co.uk" % year


# Reading mailboxes
email_extract_re = re.compile(r"([a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)", re.IGNORECASE)


def extract_email_addresses(email_line):
    return email_extract_re.findall(email_line)


class NoSuchList(ValueError):
    pass


class MailAccessDenied(ValueError):
    pass


def _get_camps(year=None, slug=None):
    from cciw.cciwmain.models import Camp
    camps = Camp.objects.filter(year=int(year))
    if slug is not None:
        camps = camps.filter(camp_name__slug=slug)
    return camps


def _get_camp(year=None, slug=None):
    try:
        return _get_camps(year=year, slug=slug).get()
    except Camp.DoesNotExist:
        raise NoSuchList(f"year={year!r} camp={slug!r}")


def _camp_officers(year=None, slug=None):
    return camp_officer_list(_get_camp(year=year, slug=slug))


def _webmasters():
    User = get_user_model()
    return User.objects.filter(is_superuser=True)


def _camp_slackers(year=None, slug=None):
    return camp_slacker_list(_get_camp(year=year, slug=slug))


def _camp_leaders(year=None, slug=None):
    camps = _get_camps(year=year, slug=slug)
    s = set()
    for c in camps:
        s.update(_get_leaders_for_camp(c))

    return list(s)


def _committee_users():
    return get_group_users(COMMITTEE_GROUP_NAME)


def _is_in_committee_or_superuser(email):
    return (get_group_users(COMMITTEE_GROUP_NAME).filter(email__iexact=email).exists() or
            _is_superuser(email))


def _get_leaders_for_camp(camp):
    retval = set()
    for p in camp.leaders.all():
        for u in p.users.all():
            retval.add(u)
    return retval


def _email_match(email, users):
    return any(user.email.lower() == email.lower() for user in users)


def _is_camp_leader_or_admin(email, year=None, slug=None):
    camps = _get_camps(year=year, slug=slug)
    all_users = set()
    for c in camps:
        all_users.update(_get_leaders_for_camp(c))
        all_users.update(list(c.admins.all()))

    return _email_match(email, all_users)


def _is_camp_leader_or_admin_or_dbs_officer_or_superuser(email, year=None, slug=None):
    if _is_camp_leader_or_admin(email, year=year, slug=slug):
        return True

    if _email_match(email, get_camp_admin_group_users()):
        return True

    if get_group_users(DBS_OFFICER_GROUP_NAME).filter(email__iexact=email).exists():
        return True

    if _is_superuser(email):
        return True

    return False


def _is_superuser(email):
    User = get_user_model()
    return User.objects.filter(email__iexact=email, is_superuser=True).exists()


def _mail_debug_users():
    User = get_user_model()
    return User.objects.filter(is_superuser=True)


# Mailing list names are used as keys when updating Routes on Mailgun. Regexes
# are used here and in Mailgun routes.

# See also above functions which generate these email addresses.

CAMP_OFFICERS_LIST = "Camp officers"
CAMP_SLACKERS_LIST = "Camp slackers"
CAMP_LEADERS_LIST = "Camp leaders"
CAMP_LEADERS_FOR_YEAR_LIST = "Camp leaders for year"
CAMP_DEBUG = "Debug"
COMMITTEE = "Committee"
WEBMASTERS = "Webmasters"


@attr.s
class EmailListGroup(object):
    name = attr.ib()
    address_matcher = attr.ib()
    get_members = attr.ib()
    has_permission = attr.ib()
    list_reply = attr.ib()

    def match(self, address, from_address):
        """
        Returns an EmailList for the given address if it matches
        this group of lists.

        If no match, returns None
        If the from_address doesn't have permission, raises MailAccessDenied
        """
        m = self.address_matcher.match(address)
        if m is None:
            return None
        captures = m.groupdict()
        if not self.has_permission(from_address, **captures):
            raise MailAccessDenied()
        return EmailList(address, self.get_members(**captures), self.list_reply)


@attr.s
class EmailList(object):
    address = attr.ib()
    members = attr.ib()
    list_reply = attr.ib()


EMAIL_LISTS = [
    EmailListGroup(
        CAMP_OFFICERS_LIST,
        re.compile(r"^camp-(?P<year>\d{4})-(?P<slug>[^/]+)-officers@cciw\.co\.uk$", re.IGNORECASE),
        _camp_officers,
        _is_camp_leader_or_admin,
        False),
    EmailListGroup(
        CAMP_SLACKERS_LIST,
        re.compile(r"^camp-(?P<year>\d{4})-(?P<slug>[^/]+)-slackers@cciw\.co\.uk$", re.IGNORECASE),
        _camp_slackers,
        _is_camp_leader_or_admin,
        False),
    EmailListGroup(
        CAMP_LEADERS_LIST,
        re.compile(r"^camp-(?P<year>\d{4})-(?P<slug>[^/]+)-leaders@cciw\.co\.uk$", re.IGNORECASE),
        _camp_leaders,
        _is_camp_leader_or_admin_or_dbs_officer_or_superuser,
        False),
    EmailListGroup(
        CAMP_LEADERS_FOR_YEAR_LIST,
        re.compile(r"^camps-(?P<year>\d{4})-leaders@cciw\.co\.uk$", re.IGNORECASE),
        _camp_leaders,
        _is_camp_leader_or_admin_or_dbs_officer_or_superuser,
        True),
    EmailListGroup(
        CAMP_DEBUG,
        re.compile(r"^camp-debug@cciw\.co\.uk$"),
        _mail_debug_users,
        lambda email: True,
        True),
    EmailListGroup(
        COMMITTEE,
        re.compile(r"^committee@cciw\.co\.uk$"),
        _committee_users,
        _is_in_committee_or_superuser,
        True),
    EmailListGroup(
        WEBMASTERS,
        re.compile(r"webmaster@cciw\.co\.uk|noreply@cciw\.co\.uk"),
        _webmasters,
        lambda email: True,  # Need to allow all temporarily to confirm address with SES
        False,
    ),
]


def find_list(address, from_addr):
    for e in EMAIL_LISTS:
        m = e.match(address, from_addr)
        if m is not None:
            return m
    raise NoSuchList()


def forward_email_to_list(mail, email_list, debug=False):
    orig_from_addr = mail['From']

    if email_list.list_reply:
        mail['Sender'] = email_list.address
        mail['List-Post'] = f'<mailto:{email_list.address}>'
    else:
        mail['Sender'] = settings.SERVER_EMAIL
    del mail['From']
    mail['From'] = mangle_from_address(orig_from_addr)
    mail['X-Original-From'] = orig_from_addr
    mail['Return-Path'] = settings.SERVER_EMAIL
    mail['Reply-To'] = orig_from_addr

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
    # re-trying won't re-send emails that were already sent.

    messages_to_send = []
    for user in email_list.members:
        addr = formatted_email(user)
        del mail['To']
        mail['To'] = addr
        # Need new message ID, or some mail servers will only send one
        del mail['Message-ID']
        mail['Message-ID'] = make_msgid()
        mail_as_bytes = force_bytes(mail.as_string())
        from_address = mail['From']
        messages_to_send.append(
            (addr, from_address, mail_as_bytes)
        )

    if len(messages_to_send) == 0:
        return

    errors = []
    for to_addr, from_address, mail_as_bytes in messages_to_send:
        if debug:
            with open(".mailing_list_log", "ab") as f:
                f.write(mail_as_bytes)
        try:
            send_mime_message(to_addr, from_address, mail_as_bytes)
        except Exception as e:
            errors.append((addr, e))

    if len(errors) == len(messages_to_send):
        # Probably a temporary error. By re-raising the last error, we cancel
        # everything, and can retry the whole email, because Mailgun will
        # re-attempt if we return 500 from the handler.
        raise errors[-1][1]

    if errors:
        # Attempt to report problem
        try:
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
        except Exception:
            # Don't raise any exceptions here, because doing so will cause the
            # whole email sending to fail and therefore be retried, despite the
            # fact that we've sent the email successfully to some users.
            pass


def mangle_from_address(address):
    address = address.replace("@", "(at)").replace("<", "").replace(">", "")
    address = address + " via <noreply@cciw.co.uk>"
    return address


def handle_mail_async(data):
    fd, name = tempfile.mkstemp(prefix="mailgun-incoming-")
    os.write(fd, data)
    os.close(fd)
    manage_py_path = os.path.join(settings.PROJECT_ROOT, "manage.py")
    os.spawnlp(os.P_NOWAIT, "nohup", "nohup", manage_py_path, "handle_message", name)


def handle_mail(data, debug=False):
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

    from_email = extract_email_addresses(mail['From'])[0]

    for address in addresses:
        try:
            email_list = find_list(address, from_email)
            forward_email_to_list(mail, email_list, debug=debug)
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
            # address, just ignore
            pass


def known_officer_email_address(address):
    User = get_user_model()
    if User.objects.filter(email__iexact=address).exists():
        return True
    if Application.objects.filter(address_email__iexact=address).exists():
        return True
    return False
