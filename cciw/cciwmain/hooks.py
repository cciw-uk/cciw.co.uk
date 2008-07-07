from cciw.cciwmain import signals
from django.dispatch import dispatcher
from cciw.mail.lists import create_mailboxes
dispatcher.connect(create_mailboxes, signal=signals.camp_created)
