# Hooks for various events
from cciw.officers import signals
from cciw.officers.email import send_application_emails

send_application_emails_w = lambda sender, **kwargs: send_application_emails(sender)
signals.application_saved.connect(send_application_emails_w)
