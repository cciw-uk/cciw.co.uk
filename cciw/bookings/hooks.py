import re

from django.db.models.signals import post_save, post_delete
from paypal.standard.ipn.signals import payment_was_successful, payment_was_flagged

from .signals import places_confirmed
from .email import send_unrecognised_payment_email, send_places_confirmed_email
from .models import BookingAccount, ChequePayment, RefundPayment, send_payment

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

    try:
        account = BookingAccount.objects.get(id=int(m.groups()[0]))
        send_payment(ipn_obj.mc_gross, account, ipn_obj)
    except BookingAccount.DoesNotExist:
        unrecognised_payment(ipn_obj)


def cheque_payment_received(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(instance.amount, instance.account, instance)


def cheque_payment_deleted(sender, **kwargs):
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
    bookings = sender
    send_places_confirmed_email(bookings, **kwargs)


#### Wiring ####

payment_was_successful.connect(paypal_payment_received)
payment_was_flagged.connect(unrecognised_payment)
places_confirmed.connect(places_confirmed_handler)
post_save.connect(cheque_payment_received, sender=ChequePayment)
post_delete.connect(cheque_payment_deleted, sender=ChequePayment)
post_save.connect(refund_payment_sent, sender=RefundPayment)
post_delete.connect(refund_payment_deleted, sender=RefundPayment)
