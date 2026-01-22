import email
from email import policy

import mailer.engine
import pytest
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.test.utils import override_settings


def send_queued_mail():
    # We need to ensure we don't send real emails.
    with override_settings(MAILER_EMAIL_BACKEND="cciw.mail.tests.QueuedMailTestMailBackend"):
        mailer.engine.send_all()


class EmailSubjectAssertionError(AssertionError):
    pass


class CheckSubjectMixin:
    def check_messages(self, messages):
        # Subject check
        for m in messages:
            if not m.subject.startswith("[CCIW]"):
                if not _is_forwarded_message(m):
                    raise EmailSubjectAssertionError(f'Email with subject "{m.subject}" should start with [CCIW]')


class TestMailBackend(CheckSubjectMixin, LocMemEmailBackend):
    __test__ = False

    def send_messages(self, messages):
        self.check_messages(messages)

        return super().send_messages(messages)


class QueuedMailTestMailBackend(CheckSubjectMixin, BaseEmailBackend):
    # Same as Django's locmem EmailBackend, but uses CheckSubjectMixin
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(mail, "outbox"):
            mail.outbox = []

    def send_messages(self, messages):
        self.check_messages(messages)
        msg_count = 0
        for message in messages:
            message.message()  # .message() triggers header validation
            mail.outbox.append(message)
            msg_count += 1
        return msg_count


def _is_forwarded_message(raw_message):
    message = email.message_from_bytes(raw_message.message().as_bytes(), policy=policy.SMTP)
    return "X-Original-From" in message


# Check that our TestMailBackend stuff above is actually working
@pytest.mark.django_db
def test_TestMailBackend_check_messages():
    with pytest.raises(EmailSubjectAssertionError):
        mail.send_mail(
            subject="This doesn't start with the right prefix",
            message="test",
            from_email="f@example.com",
            recipient_list=["to@example.com"],
        )


# And in a class:
class TestTestMailBackend:
    def test_check_messages(self):
        with pytest.raises(EmailSubjectAssertionError):
            mail.send_mail(
                subject="This doesn't start with the right prefix",
                message="test",
                from_email="f@example.com",
                recipient_list=["to@example.com"],
            )
