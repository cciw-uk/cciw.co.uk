from django.db.models.signals import post_save

from cciw.cciwmain import signals
from cciw.cciwmain.models import CampName, generate_colors_less
from cciw.mail.lists import create_mailboxes

create_mailboxes_w = lambda sender, **kwargs: create_mailboxes(sender)
signals.camp_created.connect(create_mailboxes_w)

generate_colors_less_w = lambda sender, **kwargs: generate_colors_less()
post_save.connect(generate_colors_less_w, CampName)
