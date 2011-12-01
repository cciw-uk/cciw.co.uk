from datetime import datetime
import os
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
import zc.lockfile

from cciw.bookings.models import Payment


# When processing payments, we need to alter the BookingAccount.total_received
# field, and may need to deal with concurrency. One solution would be
# serializable database transations, but this has its own complications
# (database support especially). Even with database support, there may be cases
# where a transaction has to be retried, and it is best not to do this in the
# context of HTTP handling where a user is waiting.
#
# Instead, we arrange for updates to BookingAccount.total_received to be done in
# a separate process, which can have its own transaction management, and/or
# another mechanism to ensure serialized requests.
#
# To support this, the Payment model keeps track of payments to be created.  Any
# function that needs to transfer funds into an account uses
# 'cciw.bookings.models.send_payment', which creates Payment objects for later
# processing, rather than calling BookingAccount.receive_payment directly.
#
# Thos process_payments management command is always run in a separate process,
# so doesn't have the transaction management of web requests, but a manual
# transaction around each payment processed. We use a file lock to guarantee
# serial access, rather than rely on serializable transaction isolation level.
#
# The management command is run in two ways:
# - via a non-waiting os.spawn() call, triggered from web requests or anything
#   else that causes a Payment object to be created. This ensures
#   the db is updated ASAP.
# - as a cron job, every minute, to ensure that nothing slips through the cracks.
#
# The Payment objects also act as a log of everything that has happened
# to the BookingAccount.total_received field.


@transaction.commit_on_success
def process_one_payment(payment):
    payment.account.receive_payment(payment.amount)
    payment.processed = datetime.now()
    payment.save()


class Command(BaseCommand):

    def handle(self, *args, **options):

        # Silence warnings about lock files from zc.lockfile
        logging.basicConfig()
        logger = logging.getLogger('zc.lockfile')
        logger.setLevel(logging.CRITICAL)

        # We use a lock that errors if the lock already exists, and we quit if
        # so. This is done to ensure we don't have a pile up of processes waiting
        # to process payments in the (unlikely) event of lots of payments received.
        # The scheduled run of this command should clean up any Payment objects
        # that get missed because of this strategy.

        try:
            l = zc.lockfile.LockFile(os.path.join(os.environ['HOME'], '.cciw_process_payments_lock'))
        except zc.lockfile.LockError:
            return

        try:
            for payment in Payment.objects.filter(processed__isnull=True).order_by('created'):
                try:
                    process_one_payment(payment)
                except Exception:
                    # Send email, but carry on with next payment
                    from cciw.cciwmain.common import exception_notify_admins
                    try:
                        exception_notify_admins('CCIW booking - payment processing error')
                    except Exception:
                        # Exception sending email - that's the most likely cause
                        # of process_one_payment failing, since it can
                        # indirectly cause email to be sent. In that case, the
                        # admin notification is likely to fail too.
                        continue

        finally:
            l.close()

