from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from cciw.bookings.models import Booking
from cciw.bookings.email import send_booking_expiry_mail

class Command(BaseCommand):

    def handle(self, *args, **options):

        now = datetime.now()
        nowplus12h = now + timedelta(0.5)

        unconfirmed = Booking.objects.unconfirmed().order_by('account')
        to_warn = unconfirmed.filter(booking_expires__lt=nowplus12h)
        to_expire = unconfirmed.filter(booking_expires__lt=now)

        # We do the 'to_expire' first, so we don't warn those that have already
        # expired (works since query sets are lazy)
        for booking_set, expired in [(to_expire, True),
                                     (to_warn, False)]:
            groups = []
            last_account_id = None
            for b in booking_set:
                if last_account_id is None or b.account_id != last_account_id:
                    group = []
                    groups.append(group)
                group.append(b)
                last_account_id = b.account_id

            for group in groups:
                if expired:
                    for b in group:
                        b.expire()
                        b.save()
                send_booking_expiry_mail(group[0].account, group, expired)
