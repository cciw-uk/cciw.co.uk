import email
import imaplib
import re
import xmlrpc.client

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import get_connection, make_msgid, send_mail
from django.utils.encoding import force_bytes

from cciw.auth import get_camp_admin_group_users
from cciw.cciwmain.decorators import email_errors_silently
from cciw.cciwmain.models import Camp
from cciw.cciwmain.utils import is_valid_email
from cciw.officers.email_utils import formatted_email
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.webfaction import webfaction_session


# External utility functions #


# See also below for changes to format
def address_for_camp_officers(camp):
    return "camp-%s-officers@cciw.co.uk" % camp.slug_name_with_year


def address_for_camp_slackers(camp):
    return "camp-%s-slackers@cciw.co.uk" % camp.slug_name_with_year


def address_for_camp_leaders(camp):
    return "camp-%s-leaders@cciw.co.uk" % camp.slug_name_with_year


def address_for_camp_leaders_year(year):
    return "camps-%d-leaders@cciw.co.uk" % year


# Creation of mailboxes
@email_errors_silently
def create_mailboxes(camp):
    s = webfaction_session()
    if s is None:  # WEBFACTION_USER not set
        return
    for address in [address_for_camp_officers(camp),
                    address_for_camp_slackers(camp),
                    address_for_camp_leaders(camp),
                    address_for_camp_leaders_year(camp.year)]:
        try:
            s.create_email(address, settings.LIST_MAILBOX_NAME)
        except xmlrpc.client.Fault as e:
            if e.faultString == 'username: Value already exists':
                pass
            else:
                raise

# Reading mailboxes
email_extract_re = re.compile(r"([a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)", re.IGNORECASE)


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
        raise NoSuchList("year=%r camp=%r" % (year, slug))


def _camp_officers(year=None, slug=None):
    return camp_officer_list(_get_camp(year=year, slug=slug))


def _camp_slackers(year=None, slug=None):
    return camp_slacker_list(_get_camp(year=year, slug=slug))


def _camp_leaders(year=None, slug=None):
    camps = _get_camps(year=year, slug=slug)
    s = set()
    for c in camps:
        s.update(_get_leaders_for_camp(c))

    return list(s)


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


def _is_camp_leader_or_admin_or_site_admin(email, year=None, slug=None):
    if _is_camp_leader_or_admin(email, year=year, slug=slug):
        return True

    if _email_match(email, get_camp_admin_group_users()):
        return True

    User = get_user_model()
    if User.objects.filter(email__iexact=email, is_superuser=True).exists():
        return True

    return False


def _mail_debug_users():
    User = get_user_model()
    return User.objects.filter(is_superuser=True)


# See also cciw.officers.utils
email_lists = {
    re.compile(r"^camp-(?P<year>\d{4})-(?P<slug>[^/]+)-officers@cciw.co.uk$", re.IGNORECASE):
    (_camp_officers, _is_camp_leader_or_admin),
    re.compile(r"^camp-(?P<year>\d{4})-(?P<slug>[^/]+)-slackers@cciw.co.uk$", re.IGNORECASE):
    (_camp_slackers, _is_camp_leader_or_admin),
    re.compile(r"^camp-(?P<year>\d{4})-(?P<slug>[^/]+)-leaders@cciw.co.uk$", re.IGNORECASE):
    (_camp_leaders, _is_camp_leader_or_admin_or_site_admin),
    re.compile(r"^camps-(?P<year>\d{4})-leaders@cciw.co.uk$", re.IGNORECASE):
    (_camp_leaders, _is_camp_leader_or_admin_or_site_admin),
    re.compile(r"^camp-debug@cciw.co.uk$"):
    (_mail_debug_users, lambda email: True)
}


def users_for_address(address, from_addr):
    for pat, (func, perm_func) in email_lists.items():
        m = pat.match(address)
        if m is not None:
            if not perm_func(from_addr, **m.groupdict()):
                raise MailAccessDenied()
            return func(**m.groupdict())
    raise NoSuchList()


def forward_email_to_list(mail, user_list, original_to, debug=False):
    orig_from_addr = mail['From']

    sender_addr = "CCIW lists <lists@cciw.co.uk>"
    mail['Sender'] = sender_addr
    mail['Return-Path'] = "website@cciw.co.uk"
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
    ]
    mail._headers = [(name, val) for name, val in mail._headers
                     if name.lower() in good_headers]

    # Use Django's wrapper object for connection,
    # but not the message.
    c = get_connection("django.core.mail.backends.smtp.EmailBackend")
    c.open()
    # send individual emails
    for user in user_list:
        addr = formatted_email(user)
        del mail['To']
        mail['To'] = addr
        # Need new message ID, or webfaction's mail server will only send one
        del mail['Message-ID']
        mail['Message-ID'] = make_msgid()
        mail_as_bytes = force_bytes(mail.as_string())
        if debug:
            with open(".mailing_list_log", "ab") as f:
                f.write(mail_as_bytes)

        c.connection.sendmail(sender_addr, [addr], mail_as_bytes)
    c.close()


def extract_email_addresses(email_line):
    return email_extract_re.findall(email_line)


def handle_mail(data, debug=False):
    """
    Forwards an email to the correct list of people.
    data is RFC822 formatted data
    """
    mail = email.message_from_string(data.decode('utf-8'))
    to = mail['To']
    assert to is not None, "Message did not have 'To' field set, cannot send email"

    if is_valid_email(to):
        addresses = [to]
    else:
        addresses = set([a.lower() for a in extract_email_addresses(to)])

    from_email = extract_email_addresses(mail['From'])[0]

    for address in addresses:

        try:
            l = users_for_address(address, from_email)
            forward_email_to_list(mail, l, address, debug=debug)
        except MailAccessDenied:
            send_mail("Access to mailing list {0} denied".format(address),
                      "You attempted to email the list {0}\n"
                      "with an email titled \"{1}\".\n"
                      "\n"
                      "However, you do not have permission to email this list, sorry.".format(address,
                                                                                              mail['Subject']),
                      settings.DEFAULT_FROM_EMAIL,
                      [from_email])
        except NoSuchList:
            # addresses can contain anything else on the 'to' line, which
            # can even included valid @cciw.co.uk that we don't know about
            # (e.g. other mailboxes).  So if we don't recognise the
            # address, just ignore
            pass


def handle_all_mail(debug=False):
    # We do error handling just using asserts here and catching all errors in
    # calling routine
    im = imaplib.IMAP4_SSL(settings.IMAP_MAIL_SERVER)
    im.login(settings.LIST_MAILBOX_NAME, settings.MAILBOX_PASSWORD)
    # If mail was successfully forwarded, we need to delete it and close the
    # mailbox to actually delete the items.  Otherwise, some exception that
    # occurs later could cause the deleted messages to stay undeleted and be
    # handled again.  So, we have to select the mailbox every time.
    cont = True
    while cont:
        typ, data = im.select("INBOX")
        assert typ == 'OK'
        typ, data = im.search(None, 'ALL')
        assert typ == 'OK'
        if len(data[0]) > 0:
            # handle the first one, then close the box
            num = data[0].split()[0]
            typ, data = im.fetch(num, '(RFC822)')
            assert typ == 'OK'
            handle_mail(data[0][1], debug=debug)
            typ, data = im.store(num, '+FLAGS', '\\Deleted')
            assert typ == 'OK'
            typ, data = im.close()
            assert typ == 'OK'
        else:
            cont = False
    im.logout()
