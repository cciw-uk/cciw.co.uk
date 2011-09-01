import re

from paypal.standard.ipn.signals import payment_was_successful, payment_was_flagged

from .signals import places_confirmed
from .email import send_unrecognised_payment_email, send_places_confirmed_email
from .models import BookingAccount

#### Handlers #####

### Payments ####

def unrecognised_payment(ipn_obj, **kwargs):
    send_unrecognised_payment_email(ipn_obj)


def paypal_payment_received(sender, **kwargs):
    ipn_obj = sender
    m = re.match("account:(\d+);", ipn_obj.custom)
    if m is None:
        unrecognised_payment(ipn_obj)
        return

    try:
        account = BookingAccount.objects.get(id=int(m.groups()[0]))
        account.receive_payment(ipn_obj.mc_gross)
    except BookingAccount.DoesNotExist:
        unrecognised_payment(ipn_obj)


### Place confirmation ###

def places_confirmed_handler(sender, **kwargs):
    bookings = sender
    send_places_confirmed_email(bookings, **kwargs)


#### Wiring ####

payment_was_successful.connect(paypal_payment_received)
payment_was_flagged.connect(unrecognised_payment)
places_confirmed.connect(places_confirmed_handler)
