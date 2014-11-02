import os
import logging

from django.core.management.base import BaseCommand
import zc.lockfile

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
# To support this, the Payment model keeps track of payments to be credited
# against an account. Any function that needs to transfer funds into an account
# uses 'cciw.bookings.models.send_payment', which creates Payment objects for
# later processing, rather than calling BookingAccount.receive_payment directly.
#
# The Payment model also allows payments from multiple sources to be handled
# - the Payment has a GenericForeignKey to the source object, which could
# be a PayPal payment object, or a ManualPayment object.
#
# This process_payments management command is always run in a separate process,
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
# The Payment objects also act as a log of everything that has happened to the
# BookingAccount.total_received field. Payment objects are never deleted - if,
# for example, a ManualPayment object is deleted because of an entry error, a
# new (negative) Payment object is created.


from cciw.bookings.models import process_all_payments

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
            process_all_payments()
        finally:
            l.close()
