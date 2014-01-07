import re

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from paypal.standard.ipn.signals import payment_was_successful, payment_was_flagged, payment_was_refunded, payment_was_reversed

from .signals import places_confirmed
from .email import send_unrecognised_payment_email, send_places_confirmed_email
from .models import BookingAccount, ManualPayment, RefundPayment, Payment, send_payment

#### Handlers #####

### Payments ####

def unrecognised_payment(sender=None, **kwargs):
    send_unrecognised_payment_email(sender)


def paypal_payment_received(sender, **kwargs):
    ipn_obj = sender
    m = re.match("account:(\d+);", ipn_obj.custom)
    if m is None:
        unrecognised_payment(ipn_obj)
        return

    if ipn_obj.payment_status.lower().strip() not in \
            ['completed', 'canceled_reversal', 'refunded']:
        unrecognised_payment(ipn_obj)
        return

    try:
        account = BookingAccount.objects.get(id=int(m.groups()[0]))
        send_payment(ipn_obj.mc_gross, account, ipn_obj)
    except BookingAccount.DoesNotExist:
        unrecognised_payment(ipn_obj)


def manual_payment_received(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(instance.amount, instance.account, instance)


def manual_payment_deleted(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(-instance.amount, instance.account, instance)


def refund_payment_sent(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(-instance.amount, instance.account, instance)


def refund_payment_deleted(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(instance.amount, instance.account, instance)


### Place confirmation ###

def places_confirmed_handler(sender, **kwargs):
    bookings = kwargs.pop('bookings')
    send_places_confirmed_email(bookings, **kwargs)


#### Wiring ####

payment_was_successful.connect(paypal_payment_received)
payment_was_refunded.connect(paypal_payment_received)
payment_was_reversed.connect(paypal_payment_received)
payment_was_flagged.connect(unrecognised_payment)
places_confirmed.connect(places_confirmed_handler)
post_save.connect(manual_payment_received, sender=ManualPayment)
post_delete.connect(manual_payment_deleted, sender=ManualPayment)
post_save.connect(refund_payment_sent, sender=RefundPayment)
post_delete.connect(refund_payment_deleted, sender=RefundPayment)
