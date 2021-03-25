import re
from unittest import mock

import mailer.engine
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.test.client import RequestFactory
from django.test.utils import override_settings
from mailer.models import Message
from requests.exceptions import ConnectionError

from cciw.accounts.models import COMMITTEE_ROLE_NAME, Role, User
from cciw.cciwmain.tests.utils import set_thisyear
from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.utils.functional import partition
from cciw.utils.tests.base import TestBase

from . import views
from .lists import MailAccessDenied, NoSuchList, extract_email_addresses, find_list, handle_mail, mangle_from_address
from .test_data import AWS_BOUNCE_NOTIFICATION, AWS_MESSAGE_ID, AWS_SNS_NOTIFICATION


def b(s):
    return bytes(s, 'ascii')


def partition_mailing_list_rejections(messages):
    return partition(lambda m: re.match(r'\[CCIW\] Access to mailing list .* denied', m.subject), messages)


class TestMailingLists(ExtraOfficersSetupMixin, set_thisyear(2000), TestBase):
    # Tests for mailing list sending. Note that because we are forwarding on raw
    # MIME objects with minimal changes, we are using
    # cciw.mail.smtp.RawEmailMessage, and that means we have to test most things
    # about messages using `email.message().as_bytes()`

    def setUp(self):
        super().setUp()
        User.objects.filter(is_superuser=True).update(is_superuser=False)
        User.objects.create(username="admin1",
                            email="admin1@admin.com",
                            is_superuser=True)
        User.objects.create(username="admin2",
                            email="admin2@admin.com",
                            is_superuser=True)
        User.objects.create(username="joe",
                            email="joe@gmail.com")

    def test_invalid_list(self):
        self.assertRaises(NoSuchList,
                          lambda: find_list('everyone@mailtest.cciw.co.uk', 'joe@random.com'))
        self.assertRaises(NoSuchList,
                          lambda: find_list('x-camp-2000-blue-officers@mailtest.cciw.co.uk', 'joe@random.com'))
        self.assertRaises(NoSuchList,
                          lambda: find_list('camp-2000-neon-officers@mailtest.cciw.co.uk', 'joe@random.com'))

    def test_officer_list(self):
        self.assertRaises(MailAccessDenied,
                          lambda: find_list('camp-2000-blue-officers@mailtest.cciw.co.uk',
                                            'joe@random.com'))

        self.assertRaises(MailAccessDenied,
                          lambda: find_list('camp-2000-blue-officers@mailtest.cciw.co.uk',
                                            self.officer1.email))

        officer_list = find_list('camp-2000-blue-officers@mailtest.cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        self.assertEqual([u.username for u in officer_list.get_members()],
                         ["fredjones", "joebloggs", "petersmith"])

    def test_debug_list(self):
        self.assertEqual(sorted([u.email for u in
                                 find_list('camp-debug@mailtest.cciw.co.uk', 'anyone@gmail.com').get_members()]),
                         ['admin1@admin.com', 'admin2@admin.com'])

    def test_leader_list(self):
        leader_user = self.leader_user

        # Permissions

        # Officer/non-privileged
        self.assertRaises(MailAccessDenied,
                          lambda: find_list('camps-2000-leaders@mailtest.cciw.co.uk',
                                            self.officer1.email))

        # superuser:
        l1 = find_list('camp-2000-blue-leaders@mailtest.cciw.co.uk', 'ADMIN1@ADMIN.COM')

        # leader:
        l2 = find_list('camp-2000-blue-leaders@mailtest.cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        # DBS officer
        l3 = find_list('camp-2000-blue-leaders@mailtest.cciw.co.uk', 'DBSOFFICER@somewhere.com')

        # Contents
        members = set(find_list('camps-2000-leaders@mailtest.cciw.co.uk',
                                leader_user.email).get_members())
        assert members == {self.leader_user}

        for email_list in [l1, l2, l3]:
            assert email_list.get_members() == members
            assert email_list.address == 'camp-2000-blue-leaders@mailtest.cciw.co.uk'

    def test_handle_debug_list(self):
        handle_mail(MSG_DEBUG_LIST)
        self.assertEqual(len(mail.outbox), 2)
        sent_messages_bytes = [m.message().as_bytes() for m in mail.outbox]
        to_addresses = [e for m in mail.outbox for e in m.to]
        self.assertEqual(list(sorted(to_addresses)),
                         ["admin1@admin.com",
                          "admin2@admin.com"])
        self.assertTrue(all(m.from_email == "Joe joe(at)gmail.com via <noreply@cciw.co.uk>"
                            for m in mail.outbox))
        self.assertTrue(all(b"\nX-Original-From: Joe <joe@gmail.com>" in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(b"Subject: Test" in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(b"X-Original-To: camp-debug@mailtest.cciw.co.uk" in m
                            for m in sent_messages_bytes))

    def test_handle_role_list(self):
        committee, _ = Role.objects.get_or_create(name=COMMITTEE_ROLE_NAME)
        committee.allow_emails_from_public = False
        committee.email = 'committee@mailtest.cciw.co.uk'
        committee.save()
        for name, email in [('aman1', 'a.man@example.com'),
                            ('awoman1', 'a.woman@example.com')]:
            committee.email_recipients.create(
                username=name,
                email=email,
            )

        # Email address without permission
        msg = MSG_COMMITTEE_LIST.replace(b'a.woman@example.com', b'joe@gmail.com')
        handle_mail(msg)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(rejections), 1)
        self.assertEqual(len(sent_messages), 0)

        # Email address with permission
        handle_mail(MSG_COMMITTEE_LIST)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]
        sent_to_addresses = list(sorted([address for m in sent_messages for address in m.recipients()]))
        self.assertEqual(sent_to_addresses,
                         ["a.man@example.com",
                          "a.woman@example.com"])
        self.assertTrue(all(b"Sender: committee@mailtest.cciw.co.uk" in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(b"List-Post: <mailto:committee@mailtest.cciw.co.uk>" in m
                            for m in sent_messages_bytes))

    def test_handle_public_role_list(self):
        role = Role.objects.create(
            name='Some role',
            email='myrole@mailtest.cciw.co.uk',
            allow_emails_from_public=True,
        )
        role.email_recipients.create(
            username='test1',
            email='test1@example.com'
        )

        # Email address without permission
        msg = MSG_COMMITTEE_LIST.replace(b'committee@mailtest', b'myrole@mailtest')
        handle_mail(msg)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(rejections), 0)
        self.assertEqual(len(sent_messages), 1)
        sent_to_addresses = list(sorted([address for m in sent_messages for address in m.recipients()]))
        self.assertEqual(sent_to_addresses, ['test1@example.com'])

        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]
        self.assertFalse(any(b"List-Post: <mailto:myrole@mailtest.cciw.co.uk>" in m
                             for m in sent_messages_bytes))

    def test_handle_officer_list(self):
        handle_mail(MSG_OFFICER_LIST)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(rejections), 0)
        self.assertEqual(len(sent_messages), 3)

        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]

        self.assertTrue(all(b'\nX-Original-From: Kevin Smith <leader@somewhere.com>' in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(m.from_email == 'Kevin Smith leader(at)somewhere.com via <noreply@cciw.co.uk>'
                            for m in sent_messages))
        self.assertTrue(all(b"Sender: CCIW website <noreply@cciw.co.uk>" in m
                            for m in sent_messages_bytes))
        self.assertTrue(any(True for m in mail.outbox if '"Fred Jones" <fredjones@somewhere.com>' in m.to))

    def test_spam_and_virus_checking(self):
        for header in [b'X-SES-Spam-Verdict: FAIL',
                       b'X-SES-Virus-Verdict: FAIL']:
            # insert header:
            msg = MSG_DEBUG_LIST.replace(b'Subject: Test',
                                         header + b'\r\n' + b'Subject: Test')
            handle_mail(msg)
            rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
            assert rejections == []
            assert sent_messages == []

    def test_extract(self):
        self.assertEqual(extract_email_addresses('Some Guy <A.Body@example.com>'),
                         ['A.Body@example.com'])

    def test_handle_mail_exception(self):
        """
        Test that if an error always occurs trying to send, handle_mail raises
        Exception. (This means that we will get error logs about it.)
        """
        with mock.patch('cciw.mail.lists.send_mime_message') as m_s:
            def connection_error():
                raise ConnectionError("Connection refused")
            m_s.side_effect = connection_error
            self.assertRaises(Exception, handle_mail, MSG_DEBUG_LIST)

    def test_handle_invalid_list(self):
        msg = MSG_DEBUG_LIST.replace(b'camp-debug@mailtest.cciw.co.uk',
                                     b'camp-1990-blue-officers@mailtest.cciw.co.uk')
        handle_mail(msg)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(sent_messages), 0)
        self.assertEqual(len(rejections), 0)

    def test_handle_partial_sending_failure(self):
        """
        Test what happens when there are SMTP errors with some recipients,
        but not all.
        """
        User.objects.create(username="admin3",
                            email="admin1@faildomain.com",
                            is_superuser=True)

        with mock.patch('cciw.mail.lists.send_mime_message') as m_s:
            def sendmail(to_address, from_address, mail_bytes):
                if to_address.endswith("@faildomain.com"):
                    raise Exception(f"We don't like {to_address}!")
                # Otherwise succeed silently
            m_s.side_effect = sendmail

            handle_mail(MSG_DEBUG_LIST)
        # We should have tried to send to all recipients
        self.assertEqual(m_s.call_count, 3)

        # Should have reported the error
        self.assertEqual(len(mail.outbox), 1)
        error_email = mail.outbox[0]
        self.assertIn("admin1@faildomain.com",
                      error_email.body)
        self.assertEqual(error_email.subject,
                         "[CCIW] Error with email to list camp-debug@mailtest.cciw.co.uk")
        self.assertEqual(error_email.to,
                         ["Joe <joe@gmail.com>"])

    def test_handle_mail_permission_denied(self):
        bad_mail = MSG_OFFICER_LIST.replace(b"leader@somewhere.com",
                                            b"joe@gmail.com")
        handle_mail(bad_mail)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(sent_messages, [])
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0].subject, "[CCIW] Access to mailing list camp-2000-blue-officers@mailtest.cciw.co.uk denied")
        self.assertIn("you do not have permission", rejections[0].body)

    def test_handle_mail_permission_denied_for_unknown(self):
        bad_mail = MSG_OFFICER_LIST.replace(b"leader@somewhere.com", b"randomer@random.com")
        handle_mail(bad_mail)
        self.assertEqual(len(mail.outbox), 0)

    def test_ses_incoming(self):
        request = make_plain_text_request(
            '/', AWS_SNS_NOTIFICATION['body'], AWS_SNS_NOTIFICATION['headers'])
        with mock.patch('cciw.aws.verify_sns_notification') as m1, \
                mock.patch('cciw.mail.views.handle_mail_from_s3_async') as m2:
            m1.side_effect = [True]  # fake verify
            response = views.ses_incoming_notification(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(m1.call_count, 1)
        self.assertEqual(m2.call_count, 1)
        self.assertEqual(m2.call_args[0][0], AWS_MESSAGE_ID.decode('ascii'))

    # TODO it would be nice to have tests for cciw/aws.py functions,
    # to ensure no regressions.

    def test_ses_bounce_for_reference(self):
        request = make_plain_text_request(
            '/', AWS_BOUNCE_NOTIFICATION['body'], AWS_BOUNCE_NOTIFICATION['headers'])
        with mock.patch('cciw.aws.verify_sns_notification') as m1:
            m1.side_effect = [True]  # fake verify
            response = views.ses_bounce_notification(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(m1.call_count, 1)

        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["a.camp.leader@example.com"])
        self.assertIn("was not received", m.body)
        self.assertIn("sent to a.referrer@example.com", m.body)
        self.assertIn("Use the following link", m.body)
        self.assertEqual(response.status_code, 200)

    def test_mangle_from_address(self):
        self.assertEqual(mangle_from_address("foo@bar.com"),
                         "foo(at)bar.com via <noreply@cciw.co.uk>")
        self.assertEqual(mangle_from_address("Mr Foo <foo@bar.com>"),
                         "Mr Foo foo(at)bar.com via <noreply@cciw.co.uk>")

    def test_invalid_characters(self):
        bad_mail = MSG_BAD_CHARACTERS
        handle_mail(bad_mail)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(sent_messages, [])
        self.assertEqual(rejections, [])


def emailify(msg):
    return msg.strip().replace("\n", "\r\n").encode('utf-8')


_EMAIL_SENDING_DISALLOWED = []


def disable_email_sending():
    _EMAIL_SENDING_DISALLOWED.append(None)


def enable_email_sending():
    _EMAIL_SENDING_DISALLOWED.pop(0)


# Most mail is sent directly, but some is specifically put on a queue, to ensure
# errors don't mess up payment processing. We 'send' and retrieve those here:
def send_queued_mail() -> list[mail.EmailMessage]:
    len_outbox_start = len(mail.outbox)
    sent_count = Message.objects.all().count()
    # mailer itself uses transactions for sending, triggering our AtomicChecksMixin
    # logic and disabling email sending using TestMailBackend:
    with override_settings(MAILER_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
        mailer.engine.send_all()
    len_outbox_end = len(mail.outbox)
    assert len_outbox_start + sent_count == len_outbox_end, \
        f"Expected {len_outbox_start} + {sent_count} == {len_outbox_end}"
    sent = mail.outbox[len_outbox_start:]
    mail.outbox[len_outbox_start:] = []
    assert len(mail.outbox) == len_outbox_start
    return sent


class TestMailBackend(LocMemEmailBackend):
    __test__ = False

    def send_messages(self, messages):
        # Transaction check
        if len(_EMAIL_SENDING_DISALLOWED) > 0:
            raise AssertionError("Normal email should not be sent within transactions, "
                                 "use queued_mail instead")

        # Subject check
        for m in messages:
            if (not m.subject.startswith('[CCIW]') and
                    b' via <noreply@cciw.co.uk>' not in m.message().as_bytes()):
                raise AssertionError(f"Email with subject \"{m.subject}\" should start with [CCIW]")

        return super(TestMailBackend, self).send_messages(messages)


MSG_DEBUG_LIST = emailify("""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: Test
From: Joe <joe@gmail.com>
To: Someone <someone@gmail.com>, camp-debug@mailtest.cciw.co.uk, "Someone Else" <else@gmail.com>
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@gmail.com>

Test message
""")

MSG_COMMITTEE_LIST = (MSG_DEBUG_LIST
                      .replace(b'camp-debug@mailtest.cciw.co.uk', b'committee@mailtest.cciw.co.uk')
                      .replace(b'joe@gmail.com', b'a.woman@example.com')
                      )

MSG_OFFICER_LIST = emailify("""
MIME-Version: 1.0
Date: Thu, 30 Jul 2015 10:39:10 +0100
To: "Camp 1 officers" <camp-2000-blue-officers@mailtest.cciw.co.uk>
Subject: Minibus Drivers
Content-Type: text/plain; charset="us-ascii"
From: Kevin Smith <leader@somewhere.com>
Content-Type: text/plain; charset=utf-8

This is a message!

""")


MSG_BAD_CHARACTERS = b"""From: "spammer" <spammer@example.com>
To: Someone <camp-debug@mailtest.cciw.co.uk>
Subject: Spam!
Date: Wed, 30 Dec 2020 05:27:50 +0300
MIME-Version: 1.0
Content-Type: multipart/alternative;
\tboundary="----=_NextPart_000_0008_TS7XG54W.442UQQSC"
Content-Language: en-us

This is a multi-part message in MIME format.

------=_NextPart_000_0008_TS7XG54W.442UQQSC
Content-Type: text/plain;
\tcharset="us-ascii"
Content-Transfer-Encoding: 7bit

Hello
\xa0
\xa0
https://spam.com/3pvXIsK
\xa0

------=_NextPart_000_0008_TS7XG54W.442UQQSC
Content-Type: text/html;
\tcharset="us-ascii"
Content-Transfer-Encoding: quoted-printable

<html>Spam!</html>
------=_NextPart_000_0008_TS7XG54W.442UQQSC--
""".replace(b'\n', b'\r\n')


def make_plain_text_request(path, body, headers):
    mangled_headers = {
        'HTTP_' + name.replace('-', '_').upper(): value
        for name, value in headers.items()
    }
    return RequestFactory().generic(
        'POST', path, data=body,
        content_type='text/plain; charset=UTF-8',
        **mangled_headers
    )
