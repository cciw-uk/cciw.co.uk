import time
from datetime import datetime

from django.db import models
from django.utils import timezone
from jsonfield import JSONField

USER_EMAIL_SENT_SESSION_KEY = 'email_sent'
USER_EMAIL_SENT_TIMESTAMP_SESSION_KEY = 'email_sent_timestamp'


class EmailNotification(models.Model):
    email = models.EmailField(db_index=True)
    timestamp = models.DateTimeField(default=timezone.now)
    event = models.CharField(max_length=50)
    # When we move to Postgres 9.4 we can switch this to
    # django.contrib.postgres.jsonb.JSONField
    data = JSONField()

    class Meta:
        ordering = ['-timestamp']

    @classmethod
    def log_event(cls, email=None, event=None, data=None):
        cls.objects.create(email=email,
                           event=event,
                           data=dict(data))

    def __str__(self):
        return "Email to {0} {1} at {2}".format(self.email, self.event, self.timestamp)

    proxy_to_data = lambda name: property(lambda self: self.data[name])
    event_check = lambda event: property(lambda self: self.event == event)

    reason = proxy_to_data('reason')
    description = proxy_to_data('description')

    is_dropped = event_check('dropped')
    is_delivered = event_check('delivered')


def log_user_email_sent(request, email_address):
    """
    Registers with the user's session the fact that an email was sent to the
    user.

    Used for tracking whether the email was delivered.
    """
    request.session[USER_EMAIL_SENT_SESSION_KEY] = email_address
    request.session[USER_EMAIL_SENT_TIMESTAMP_SESSION_KEY] = int(time.time())


def get_email_notification_for_session(request):
    if USER_EMAIL_SENT_SESSION_KEY not in request.session:
        return None
    dt = datetime.fromtimestamp(
        int(request.session[USER_EMAIL_SENT_TIMESTAMP_SESSION_KEY]),
        timezone.utc)

    # Ignore anything more than an hour ago
    if (timezone.now() - dt).seconds > 3600:
        clear_email_notification_for_session(request)
        return None

    return (EmailNotification.objects
            .filter(email=request.session[USER_EMAIL_SENT_SESSION_KEY],
                    timestamp__gte=dt)
            .first())


def clear_email_notification_for_session(request):
    del request.session[USER_EMAIL_SENT_SESSION_KEY]
    del request.session[USER_EMAIL_SENT_TIMESTAMP_SESSION_KEY]
