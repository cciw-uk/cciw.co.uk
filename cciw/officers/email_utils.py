from django.core.mail import EmailMessage, SMTPConnection, SafeMIMEText, Header, BadHeaderError, formatdate, make_msgid
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from django.conf import settings

"""
Utilities for sending email with attachments
"""

class SafeMIMEMultipart(MIMEMultipart): 
    def __setitem__(self, name, val): 
        "Forbids multi-line headers, to prevent header injection." 
        if '\n' in val or '\r' in val: 
            raise BadHeaderError, "Header values can't contain newlines (got %r for header %r)" % (val, name) 
        if name == "Subject": 
            val = Header(val, settings.DEFAULT_CHARSET) 
        MIMEMultipart.__setitem__(self, name, val) 
 
    def attachFile(self, filename, content, mimetype): 
        maintype, subtype = mimetype.split('/', 1) 
        msg = MIMEBase(maintype, subtype) 
        msg.set_payload(content) 
        Encoders.encode_base64(msg) 
        msg.add_header('Content-Disposition', 'attachment', filename=filename) 
        MIMEMultipart.attach(self, msg) 

class EmailWithAttachments(EmailMessage):
    def __init__(self, *args, **kwargs):
        attachments = kwargs.pop('attachments', None)
        super(EmailWithAttachments, self).__init__(*args, **kwargs)
        x = self.connection
        self.attachments = attachments

    def message(self):
        simple_msg = SafeMIMEText(self.body, 'plain', settings.DEFAULT_CHARSET)
        if self.attachments:
            # This is a multipart mail
            msg = SafeMIMEMultipart()
            # First the body
            msg.attach(simple_msg)
            # Then the various files to be attached.
            for (filename, content, mimetype) in self.attachments:
                msg.attachFile(filename, content, mimetype)
        else:
            msg = simple_msg
        
        msg['Subject'] = self.subject
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to)
        msg['Date'] = formatdate()
        msg['Message-ID'] = make_msgid()
        if self.bcc:
            msg['Bcc'] = ', '.join(self.bcc)
        return msg

def send_mail_with_attachments(subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None, attachments=None): 
    connection = SMTPConnection(username=auth_user, password=auth_password,
                                 fail_silently=fail_silently)
    return EmailWithAttachments(subject, message, from_email, recipient_list, connection=connection, attachments=attachments).send()

def formatted_email(user):
    """
    Get the email address plus name of the user, formatted for
    use in sending an email, or 'None' if no email address available
    """
    name = (user.first_name + " " + user.last_name).strip().replace('"', '')
    email = user.email.strip()
    if len(email) == 0:
        return None
    elif len(name) > 0:
        return '"%s" <%s>' % (name, email)
    else:
        return email
