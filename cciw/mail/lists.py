import email
import imaplib
import re

from django.conf import settings
from django.core.mail import get_connection, make_msgid
import xmlrpclib

from cciw.cciwmain.decorators import email_errors_silently
from cciw.cciwmain.utils import is_valid_email
from cciw.officers.email_utils import formatted_email
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.webfaction import webfaction_session

### External utility functions ###

# See also below for changes to format
def address_for_camp_officers(camp):
    return "camp-%d-%d-officers@cciw.co.uk" % (camp.year, camp.number)


def address_for_camp_slackers(camp):
    return "camp-%d-%d-slackers@cciw.co.uk" % (camp.year, camp.number)


def address_for_camp_leaders(camp):
    return "camp-%d-%d-leaders@cciw.co.uk" % (camp.year, camp.number)


def address_for_camp_leaders_year(year):
    return "camps-%d-leaders@cciw.co.uk" % year


### Creation of mailboxes ###
@email_errors_silently
def create_mailboxes(camp):
    s = webfaction_session()
    if s is None: # WEBFACTION_USER not set
        return
    for address in [address_for_camp_officers(camp),
                    address_for_camp_slackers(camp),
                    address_for_camp_leaders(camp),
                    address_for_camp_leaders_year(camp.year)]:
        try:
            s.create_email(address, settings.LIST_MAILBOX_NAME)
        except xmlrpclib.Fault, e:
            if e.faultString == 'username: Value already exists':
                pass
            else:
                raise

### Reading mailboxes ###
email_extract_re = re.compile(r"([a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)")


def _camp_officers(year=None, number=None):
    from cciw.cciwmain.models import Camp
    try:
        c = Camp.objects.get(year=year, number=number)
    except Camp.DoesNotExist:
        return None # address is invalid

    return map(formatted_email, camp_officer_list(c))


def _camp_slackers(year=None, number=None):
    from cciw.cciwmain.models import Camp
    try:
        c = Camp.objects.get(year=year, number=number)
    except Camp.DoesNotExist:
        return None # address is invalid

    return map(formatted_email, camp_slacker_list(c))


def _camp_leaders(year=None, number=None):
    from cciw.cciwmain.models import Camp
    camps = Camp.objects.filter(year=year)
    if number is not None:
        camps = camps.filter(number=number)
    s = set()
    for c in camps:
        s.update(_get_leaders_for_camp(c))

    return map(formatted_email, s)


def _get_leaders_for_camp(camp):
    retval = set()
    for p in camp.leaders.all():
        for u in p.users.all():
            retval.add(u)
    return retval


# See also cciw.officers.utils
email_lists = {
    re.compile(r"^camp-(?P<year>\d{4})-(?P<number>\d+)-officers@cciw.co.uk$",
               re.IGNORECASE): _camp_officers,
    re.compile(r"^camp-(?P<year>\d{4})-(?P<number>\d+)-slackers@cciw.co.uk$",
               re.IGNORECASE): _camp_slackers,
    re.compile(r"^camp-(?P<year>\d{4})-(?P<number>\d+)-leaders@cciw.co.uk$",
               re.IGNORECASE): _camp_leaders,
    re.compile(r"^camps-(?P<year>\d{4})-leaders@cciw.co.uk$",
               re.IGNORECASE): _camp_leaders,
    re.compile(r"^camp-debug@cciw.co.uk$"):
        lambda: settings.LIST_MAIL_DEBUG_ADDRESSES,
    }


def list_for_address(address):
    for pat, func in email_lists.items():
        m = pat.match(address)
        if m is not None:
            return func(**m.groupdict())
    return None


def forward_email_to_list(mail, addresslist, original_to):
    orig_from_addr = mail['From']

    new_from_addr = "lists@cciw.co.uk"
    mail['From'] = new_from_addr
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
        ]
    mail._headers = [(name, val) for name, val in mail._headers
                     if name.lower() in good_headers]

    # Use Django's wrapper object for connection,
    # but not the message.
    c = get_connection("django.core.mail.backends.smtp.EmailBackend")
    c.open()
    # send individual emails
    for addr in addresslist:
        del mail['To']
        mail['To'] = addr
        # Need new message ID, or webfaction's mail server will only send one
        del mail['Message-ID']
        mail['Message-ID'] = make_msgid()
        c.connection.sendmail(new_from_addr, [addr], mail.as_string())
    c.close()


def handle_mail(data):
    """
    Forwards an email to the correct list of people.
    data is RFC822 formatted data
    """
    mail = email.message_from_string(data)
    to = mail['To']
    assert to is not None, "Message did not have 'To' field set, cannot send email"

    if is_valid_email(to):
        addresses = [to]
    else:
        addresses = email_extract_re.findall(to)

    for address in addresses:
        l = list_for_address(address)
        # addresses can contain anything else on the 'to' line, which
        # can even included valid @cciw.co.uk that we don't know about
        # (e.g. other mailboxes).  So if we don't recognise the
        # address, just ignore
        if l is not None:
            forward_email_to_list(mail, l, address)


def handle_all_mail():
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
            handle_mail(data[0][1])
            typ, data = im.store(num, '+FLAGS', '\\Deleted')
            assert typ == 'OK'
            typ, data = im.close()
            assert typ == 'OK'
        else:
            cont = False
    im.logout()
