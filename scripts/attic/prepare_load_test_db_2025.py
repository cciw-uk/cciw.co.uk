#!/usr/bin/env python


# This was used to prepare a database on staging for doing load testing
# to replicate outage in 2025.

# Run this after running anonymise_db.py

# Then run

#  fab local-db-dump ../db_backups/load-test-2025-09-02.pgdump                                                                                                                                                   git staging-server ~/devel/cciw.co.uk/src [12:22]

# ruff: noqa:E402

import django

django.setup()

from datetime import timedelta

from django.db.models import F

from cciw.accounts.models import User
from cciw.bookings.models import (
    AccountTransferPayment,
    Booking,
    ManualPayment,
    Payment,
    PaymentSource,
    PayPalIPN,
    RefundPayment,
)
from cciw.cciwmain.models import Camp

superuser_password = input("Password for superuser: ")
user = User.objects.get(is_superuser=True)

user.set_password(superuser_password)
user.save()


Camp.objects.all().filter(year=2025).update(start_date=F("start_date") + timedelta(days=4 * 30))
Camp.objects.all().filter(year=2025).update(end_date=F("end_date") + timedelta(days=4 * 30))
Booking.objects.filter(camp__year=2025).delete()


PayPalIPN.objects.filter(payment_date__year=2025).delete()
AccountTransferPayment.objects.filter(created_at__year=2025).delete()
RefundPayment.objects.filter(created_at__year=2025).delete()
ManualPayment.objects.filter(created_at__year=2025).delete()


PaymentSource.objects.filter(
    payment__created_at__year=2025,
    manual_payment__isnull=True,
    refund_payment__isnull=True,
    write_off_debt__isnull=True,
    account_transfer_payment__isnull=True,
)
Payment.objects.filter(created_at__year=2025, processed_at__isnull=False).delete()
