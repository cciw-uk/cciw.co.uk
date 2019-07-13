import logging

from django.core.mail import EmailMessage

logger = logging.getLogger("cciw.mail.smtp")


# Wrappers for EmailMessage so that we can send our already constructed mime
# message using Django's normal mailing sending routines.

class RawEmailMessage(EmailMessage):
    def __init__(self, mime_data=b'', **kwargs):
        super().__init__(**kwargs)
        self.mime_data = mime_data

    def message(self):
        return RawBytes(self.mime_data)


class RawBytes:
    def __init__(self, bytes_data):
        self.bytes_data = bytes_data

    def as_bytes(self, **kwargs):
        return self.bytes_data


def send_mime_message(to_address, from_address, mime_message):
    logger.info("send_mime_message to=%s message=%s...", to_address, mime_message[0:50])
    email = RawEmailMessage(to=[to_address], from_email=from_address, mime_data=mime_message)
    email.send()
