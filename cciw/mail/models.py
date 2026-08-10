from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from django.core.mail import EmailMessage
from django.db import models, transaction
from django.utils import timezone


class ScheduledMailRecord(models.Model):
    """
    A generic mechanism for keeping track of emails that have been sent.
    """

    tracking_id = models.CharField(unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_sent_at = models.DateTimeField(null=True, blank=True, default=None)
    sent_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.tracking_id


type BuildEmail[T] = Callable[[T], EmailMessage]


@dataclass
class NeverRepeat:
    pass


@dataclass
class RepeatAfter:
    delta: timedelta


type Repeat = NeverRepeat | RepeatAfter


# We use django-mailer which puts everything on the queue in the
# database. This means our ScheduledMailEntry data will get saved
# along with the outgoing emails, or fail to get saved under the same
# conditions due to an exception, which is what we want.


# Bundling them all together in one transaction will make failures
# easiest to think about and handle - either the entire batch
# worked or failed.
@transaction.atomic
def send_mails_for_items_according_to_schedule[T](
    *,
    items: Sequence[T],
    tracking_id_format: Callable[[T], str],
    repeat: Repeat,
    builder: BuildEmail[T],
) -> None:
    # Do a batch load for everything that already exists, to reduce DB load.
    tracking_ids = [tracking_id_format(item) for item in items]
    existing_records_map = {
        rec.tracking_id: rec for rec in ScheduledMailRecord.objects.filter(tracking_id__in=tracking_ids)
    }

    for item in items:
        now = timezone.now()
        tracking_id = tracking_id_format(item)
        if tracking_id in existing_records_map:
            record = existing_records_map[tracking_id]
        else:
            record, _new = ScheduledMailRecord.objects.get_or_create(tracking_id=tracking_id)
        if record.sent_count == 0:
            do_send = True
        elif isinstance(repeat, NeverRepeat):
            do_send = False
        else:
            # We add a little lee-way on the delta check to cope with the fact
            # that sending a batch of emails is going to take a bit of time,
            # and we might only run the batch process e.g. once a day.
            epsilon = timedelta(hours=1)
            do_send = ((now + epsilon) - record.last_sent_at) > repeat.delta

        if do_send:
            builder(item).send()
            record.sent_count += 1
            record.last_sent_at = now
            record.save()
