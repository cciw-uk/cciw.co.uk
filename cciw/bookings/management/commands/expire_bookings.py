from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from cciw.bookings.models import Booking
from cciw.bookings.email import send_booking_expiry_mail

class Command(BaseCommand):

    def handle(self, *args, **options):

        now = datetime.now()

        # For the warning, we send out between 12 and 13 hours before booking
        # expires.  This relies on this job being run once an hour, and only
        # once an hour.
        nowplus12h = now + timedelta(0, 3600 * 12)
        nowplus13h = now + timedelta(0, 3600 * 13)

        unconfirmed = Booking.objects.unconfirmed().order_by('account')
        to_warn = unconfirmed.filter(booking_expires__lte=nowplus13h,
                                     booking_expires__gte=nowplus12h)
        to_expire = unconfirmed.filter(booking_expires__lte=now)

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
