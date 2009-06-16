from cciw.cciwmain import signals
from cciw.mail.lists import create_mailboxes

create_mailboxes_w = lambda sender, **kwargs: create_mailboxes(sender)
signals.camp_created.connect(create_mailboxes_w)
