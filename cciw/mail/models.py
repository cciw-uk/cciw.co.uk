from django.conf import settings
from django.db import models


class EmailForwardQuerySet(models.QuerySet):
    def active(self):
        return self.filter(enabled=True)


class EmailForward(models.Model):
    address = models.EmailField(help_text="Email address including domain", unique=True)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL)
    enabled = models.BooleanField(default=True)

    objects = EmailForwardQuerySet.as_manager()

    def __str__(self):
        return f'Forward {self.address} to {", ".join(u.email for u in self.recipients.all())}'



from . import hooks  # noqa
