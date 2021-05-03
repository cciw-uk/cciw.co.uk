import re
from unittest import mock

import mailer.engine
import pytest
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.test.client import RequestFactory
from django.test.utils import override_settings
from mailer.models import Message
from requests.exceptions import ConnectionError

from cciw.accounts.models import Role, User
from cciw.cciwmain.tests.base import factories as camp_factories
from cciw.cciwmain.tests.utils import set_thisyear
from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.officers.tests.base import factories as officer_factories
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
                            email="joe@example.com")

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

    def _setup_role_for_email(self, *, name='Test', email, allow_emails_from_public,
                              recipients):
        role, _ = Role.objects.get_or_create(name=name)
        role.allow_emails_from_public = allow_emails_from_public
        role.email = email
        role.save()
        for name, email in recipients:
            role.email_recipients.create(
                username=name,
                email=email,
            )
        return role

    def test_handle_role_list(self):
        role = self._setup_role_for_email(
            allow_emails_from_public=False,
            email='committee@mailtest.cciw.co.uk',
            recipients=[('aperson1', 'a.person.1@example.com'),
                        ('aperson2', 'a.person.2@example.com')]
        )

        # Email address without permission
        msg1 = make_message(
            to_email=role.email,
            from_email='joe@example.com',
        )
        handle_mail(msg1)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 1
        assert len(sent_messages) == 0

        # Email address with permission
        msg2 = make_message(
            to_email=role.email,
            from_email='Me <a.person.1@example.com>',
        )
        handle_mail(msg2)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 1
        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]
        sent_to_addresses = list(sorted([address for m in sent_messages for address in m.recipients()]))
        assert sent_to_addresses == [
            "a.person.1@example.com",
            "a.person.2@example.com",
        ]
        assert all(b"Sender: committee@mailtest.cciw.co.uk" in m
                   for m in sent_messages_bytes)
        assert all(b"List-Post: <mailto:committee@mailtest.cciw.co.uk>" in m
                   for m in sent_messages_bytes)
        assert all(m.from_email == "Me a.person.1(at)example.com via <noreply@cciw.co.uk>"
                   for m in sent_messages)
        assert all(b"\nX-Original-From: Me <a.person.1@example.com>" in m
                   for m in sent_messages_bytes)
        assert all(b"Subject: Test" in m
                   for m in sent_messages_bytes)
        assert all(b"X-Original-To: committee@mailtest.cciw.co.uk" in m
                   for m in sent_messages_bytes)

    def test_handle_public_role_list(self):
        role = self._setup_role_for_email(
            email='myrole@mailtest.cciw.co.uk',
            allow_emails_from_public=True,
            recipients=[('test1', 'test1@example.com')],
        )

        # Email address without membership
        msg = make_message(to_email=role.email, from_email='someone@example.com')
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
        camp = camp_factories.create_camp(
            year=2000,
            camp_name='Pink',
            leader=officer_factories.create_officer(email=(leader_email := 'kevin.smith@example.com')),
        )
        officer_factories.add_officers_to_camp(
            camp,
            [
                officer_factories.create_officer(
                    first_name='Fred',
                    last_name='Jones',
                    email='fredjones@example.com',
                ),
                officer_factories.create_officer(),
                officer_factories.create_officer(),
            ],
        )
        handle_mail(make_message(
            from_email=f'Kevin Smith <{leader_email}>',
            to_email='camp-2000-pink-officers@mailtest.cciw.co.uk',
        ))

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(rejections), 0)
        self.assertEqual(len(sent_messages), 3)

        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]

        self.assertTrue(all(b'\nX-Original-From: Kevin Smith <kevin.smith@example.com>' in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(m.from_email == 'Kevin Smith kevin.smith(at)example.com via <noreply@cciw.co.uk>'
                            for m in sent_messages))
        self.assertTrue(all(b"Sender: CCIW website <noreply@cciw.co.uk>" in m
                            for m in sent_messages_bytes))
        self.assertTrue(any(True for m in mail.outbox if '"Fred Jones" <fredjones@example.com>' in m.to))

    def test_spam_and_virus_checking(self):
        role = self._setup_role_for_email(
            name='Test',
            email='test@mailtest.cciw.co.uk',
            allow_emails_from_public=True,
            recipients=[('test', 'test@example.com')])
        for header in ['X-SES-Spam-Verdict: FAIL',
                       'X-SES-Virus-Verdict: FAIL']:
            msg = make_message(to_email=role.email, additional_headers=[header])
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
        role = self._setup_role_for_email(
            allow_emails_from_public=False,
            email='committee@mailtest.cciw.co.uk',
            recipients=[('aperson', 'a.person@example.com')]
        )
        with mock.patch('cciw.mail.lists.send_mime_message') as m_s:
            def connection_error():
                raise ConnectionError("Connection refused")
            m_s.side_effect = connection_error
            with pytest.raises(Exception):
                handle_mail(make_message(
                    to_email=role.email,
                    from_email='a.person@example.com'),
                )

    def test_handle_invalid_list(self):
        msg = make_message(to_email='camp-1990-blue-officers@mailtest.cciw.co.uk')
        handle_mail(msg)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(sent_messages), 0)
        self.assertEqual(len(rejections), 0)

    def test_handle_partial_sending_failure(self):
        """
        Test what happens when there are SMTP errors with some recipients,
        but not all.
        """
        role = self._setup_role_for_email(
            allow_emails_from_public=False,
            email='committee@mailtest.cciw.co.uk',
            recipients=[('aperson1', 'a.person.1@example.com'),
                        ('aperson2', 'a.person.2@example.com'),
                        ('person', 'person@faildomain.com')]
        )

        with mock.patch('cciw.mail.lists.send_mime_message') as m_s:
            def sendmail(to_address, from_address, mail_bytes):
                if to_address.endswith("@faildomain.com"):
                    raise Exception(f"We don't like {to_address}!")
                # Otherwise succeed silently
            m_s.side_effect = sendmail

            handle_mail(make_message(to_email=role.email, from_email='a.person.1@example.com'))
        # We should have tried to send to all recipients
        self.assertEqual(m_s.call_count, 3)

        # Should have reported the error
        self.assertEqual(len(mail.outbox), 1)
        error_email = mail.outbox[0]
        self.assertIn("person@faildomain.com",
                      error_email.body)
        self.assertEqual(error_email.subject,
                         "[CCIW] Error with email to list committee@mailtest.cciw.co.uk")
        self.assertEqual(error_email.to,
                         ["a.person.1@example.com"])

    def test_handle_mail_permission_denied(self):
        bad_mail = MSG_OFFICER_LIST.replace(b"leader@somewhere.com",
                                            b"joe@example.com")
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


def make_message(
        *,
        from_email='Sam <a.person@example.com>',
        to_email='someone@cciw.co.uk',
        other_to_emails=None,
        subject='Test',
        additional_headers=None,
):
    if other_to_emails is None:
        # This exists to check mail is handled properly in cases like this:
        # To: someone@example.com, mylist@cciw.co.uk
        other_to_emails = [
            'Someone <someone@example.com>'
            '"Someone Else" <someone_else@example.com>',
        ]
    else:
        other_to_emails = []
    all_to_emails = other_to_emails + [to_email]
    if additional_headers is not None:
        extra_headers = ''.join(header + '\n' for header in additional_headers)
    else:
        extra_headers = ''

    return emailify(f"""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: {subject}
From: {from_email}
To: {', '.join(all_to_emails)}
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@example.com>
{extra_headers}

Test message
    """)


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
