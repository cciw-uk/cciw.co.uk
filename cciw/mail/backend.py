from django.core.mail.backends.base import BaseEmailBackend

from django.core.mail import get_connection


# A backend that filters most emails out for testing purposes
# on the staging site.

class StagingBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        connection = get_connection(backend="django.core.mail.backends.smtp.EmailBackend")
        num_sent = 0
        for email in email_messages:
            if "booking" in email.subject:
                email.connection = connection
                email.send()
            else:
                pass # drop it
            num_sent += 1 # pretend we send them all

        return num_sent
