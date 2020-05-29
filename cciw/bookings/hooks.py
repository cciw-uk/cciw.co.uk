from django.conf import settings
from django.db.models.signals import post_delete, post_save
from paypal.standard.ipn.signals import invalid_ipn_received, valid_ipn_received

from .email import send_pending_payment_email, send_places_confirmed_email, send_unrecognised_payment_email
from .models import AccountTransferPayment, ManualPayment, RefundPayment, parse_paypal_custom_field, send_payment
from .signals import places_confirmed

# == Handlers ==

# == Payments ==


def unrecognised_payment(sender=None, reason='Invalid IPN', **kwargs):
    send_unrecognised_payment_email(sender, reason=reason)


def paypal_payment_received(sender, **kwargs):
    ipn_obj = sender
    if ipn_obj.business != settings.PAYPAL_RECEIVER_EMAIL:
        unrecognised_payment(ipn_obj, 'Incorrect receiver email')
        return

    account = parse_paypal_custom_field(ipn_obj.custom)
    if account is None:
        unrecognised_payment(ipn_obj, 'No associated account')
        return

    if ipn_obj.payment_status == "Pending":
        send_pending_payment_email(account, ipn_obj)
        return

    if (ipn_obj.payment_status not in
            ['Completed', 'Canceled_Reversal', 'Refunded']):
        unrecognised_payment(ipn_obj, f'Unrecognised payment status {ipn_obj.payment_status}')
        return

    send_payment(ipn_obj.mc_gross, account, ipn_obj)


def manual_payment_received(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(instance.amount, instance.account, instance)


def manual_payment_deleted(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(-instance.amount, instance.account, None)


def refund_payment_sent(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(-instance.amount, instance.account, instance)


def refund_payment_deleted(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(instance.amount, instance.account, None)


def account_transfer_payment_received(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(-instance.amount, instance.from_account, instance)
    send_payment(instance.amount, instance.to_account, instance)


def account_transfer_payment_deleted(sender, **kwargs):
    instance = kwargs['instance']
    send_payment(instance.amount, instance.from_account, None)
    send_payment(-instance.amount, instance.to_account, None)


# == Place confirmation ==

def places_confirmed_handler(sender, **kwargs):
    bookings = kwargs.pop('bookings')
    send_places_confirmed_email(bookings, **kwargs)


# == Wiring ==

valid_ipn_received.connect(paypal_payment_received)
invalid_ipn_received.connect(unrecognised_payment)
places_confirmed.connect(places_confirmed_handler)
post_save.connect(manual_payment_received, sender=ManualPayment)
post_delete.connect(manual_payment_deleted, sender=ManualPayment)
post_save.connect(refund_payment_sent, sender=RefundPayment)
post_delete.connect(refund_payment_deleted, sender=RefundPayment)
post_save.connect(account_transfer_payment_received, sender=AccountTransferPayment)
post_delete.connect(account_transfer_payment_deleted, sender=AccountTransferPayment)
