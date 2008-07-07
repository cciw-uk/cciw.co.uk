import email
import imaplib
import xmlrpclib
import re
from django.conf import settings 
from cciw.cciwmain.models import Camp
from cciw.officers.email_utils import formatted_email
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.webfaction import webfaction_session

### Creation of mailboxes ###

def create_mailboxes(camp):
    # TODO: handle xmlrpclib.Fault exceptions
    email_address = "camp-%d-%d-officers@cciw.co.uk" % (camp.year, camp.number)
    s = webfaction_session()
    email = s.create_email(email_address, settings.LIST_MAILBOX_NAME)

### Reading mailboxes ###

def camp_officers(year=None, number=None):
    try:
        c = Camp.objects.get(year=year, number=number)
    except Camp.DoesNotExist:
        return None # address is invalid

    return map(formatted_email, camp_officer_list(c))

def camp_slackers(year=None, number=None):
    try:
        c = Camp.objects.get(year=year, number=number)
    except Camp.DoesNotExist:
        return None # address is invalid

    return map(formatted_email, camp_slacker_list(c))

email_lists = {
    re.compile(r"^camp-(?P<year>\d{4})-(?P<number>\d+)-officers@cciw.co.uk$", 
               re.IGNORECASE): camp_officers,
    re.compile(r"^camp-(?P<year>\d{4})-(?P<number>\d+)-slackers@cciw.co.uk$",
               re.IGNORECASE): camp_slackers,
    re.compile(r"^camp-debug@cciw.co.uk$"):
        lambda: ['"Luke Plant" <L.Plant.98@cantab.net>',
                 'spookylukey@fastmail.fm']
    }

def list_for_address(address):
    for pat, func in email_lists.items():
        m = pat.match(address)
        if m is not None:
            return func(**m.groupdict())
    return None

def send_none_matched_mail(to, address):
    """
    Sends an email to $to saying that $address is not known.
    """
    # TODO
    print "No mail matched %r" % address

def forward_email_to_list(mail, addresslist, original_to):
    from_addr = mail['From']

    # search and erase the original 'To' address in the 'Received'
    # headers, to hinder people from mailing the address themselves
    mail._headers = [(name, val.replace(original_to, "private@cciw.co.uk"))
                     for name, val in mail._headers]

    # Use Django's wrapper object for connection,
    # but not the message.
    from django.core.mail import SMTPConnection
    c = SMTPConnection()
    c.open()
    # send inidividual emails
    for addr in addresslist:
        del mail['To']
        mail['To'] = addr
        c.connection.sendmail(from_addr, addresslist, mail.as_string())
    c.close()

def handle_mail(data):
    """
    Forwards an email to the correct list of people.
    data is RFC822 formatted data
    """
    mail = email.message_from_string(data)
    address = mail['To']
    assert address is not None, "Message did not have 'To' field set, cannot send email"

    l = list_for_address(address)
    if l is None:
        # indicates nothing matching this address
        send_none_matched_mail(mail['From'], address)
    else:
        forward_email_to_list(mail, l, address)

def handle_all_mail():
    # We do error handling just using asserts here
    # and catching all errors in calling routine
    im = imaplib.IMAP4_SSL(settings.IMAP_MAIL_SERVER)
    im.login(settings.LIST_MAILBOX_NAME, settings.MAILBOX_PASSWORD)
    typ, data = im.select("INBOX")
    assert typ == 'OK'
    typ, data = im.search(None, 'ALL')
    assert typ == 'OK'
    for num in data[0].split():
        typ, data = im.fetch(num, '(RFC822)')
        assert typ == 'OK'
        handle_mail(data[0][1])
        typ, data = im.store(num, '+FLAGS', '\\Deleted')
        assert typ == 'OK'
    im.close()
    im.logout()
