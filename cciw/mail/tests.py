import contextlib
from unittest import mock

import vcr
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.test.client import RequestFactory
from requests.exceptions import ConnectionError

from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.utils.tests.base import TestBase

from . import views
from .lists import MailAccessDenied, NoSuchList, handle_mail, users_for_address
from .mailgun import send_mime_message
from .test_data import MAILGUN_EXAMPLE_POST_DATA_FOR_MIME_ENDPOINT


def b(s):
    return bytes(s, 'ascii')


@contextlib.contextmanager
def mock_mailgun_send_mime():
    with mock.patch('cciw.mail.lists.send_mime_message') as m:
        # Special behaviour:
        def sendmail(to_address, mail_bytes):
            if to_address.endswith("@faildomain.com"):
                raise Exception("Mailgun doesn't like {0}!".format(to_address))
            # Otherwise succeed silently

        m.side_effect = sendmail

        # Helpers for tests:
        m.to_addresses = (
            lambda: [c[0][0] for c in m.call_args_list])
        m.messages_sent = (
            lambda: [c[0][1] for c in m.call_args_list])
        yield m


@contextlib.contextmanager
def mock_send_mail():
    with mock.patch('cciw.mail.lists.send_mail') as send_mail:
        # Helpers:
        def sent_messages(idx):
            args = send_mail.call_args_list[idx][0]
            return EmailMessage(args[0], args[1], args[2], args[3])

        send_mail.sent_messages = sent_messages
        yield send_mail


class TestMailingLists(ExtraOfficersSetupMixin, TestBase):

    def setUp(self):
        super(TestMailingLists, self).setUp()
        User = get_user_model()
        User.objects.filter(is_superuser=True).update(is_superuser=False)
        User.objects.create(username="admin1",
                            email="admin1@admin.com",
                            is_superuser=True)
        User.objects.create(username="admin2",
                            email="admin2@admin.com",
                            is_superuser=True)

    def test_handle_list(self):
        with mock_mailgun_send_mime() as m_s:
            handle_mail(MSG1)
            self.assertEqual(m_s.call_count, 2)
            messages_sent = m_s.messages_sent()
            to_addresses = m_s.to_addresses()
            self.assertEqual(list(sorted(to_addresses)),
                             ["admin1@admin.com",
                              "admin2@admin.com"])
            self.assertTrue(all(b"Sender: CCIW lists <lists@cciw.co.uk>" in m
                                for m in messages_sent))
            self.assertTrue(all(b"From: Joe <joe@gmail.com>" in m
                                for m in messages_sent))
            self.assertTrue(any(b"To: admin1@admin.com" in m
                                for m in messages_sent))
            self.assertTrue(any(b"To: admin2@admin.com" in m
                                for m in messages_sent))
            self.assertTrue(all(b"Subject: Test" in m
                                for m in messages_sent))

    def test_handle_mail_exception(self):
        """
        Test that if an error occurs trying to send, handle_mail raises
        Exception. (This means that mailgun_incoming will return
        a 500, and Mailgun will attempt to POST again)
        """
        with mock_mailgun_send_mime() as m_s:
            def connection_error():
                raise ConnectionError("Connection refused")
            m_s.side_effect = connection_error
            self.assertRaises(Exception, handle_mail, MSG1)

    def test_handle_invalid_list(self):
        with mock_mailgun_send_mime() as m_s:
            with mock_send_mail() as send_mail:
                msg = MSG1.replace(b'camp-debug@cciw.co.uk', b'camp-1990-blue-officers@cciw.co.uk')
                handle_mail(msg)
        self.assertEqual(m_s.call_count, 0)
        self.assertEqual(send_mail.call_count, 1)
        error_email = send_mail.sent_messages(0)
        self.assertIn('camp-1990-blue-officers@cciw.co.uk',
                      error_email.body)
        self.assertIn('list does not exist',
                      error_email.body)

    def test_handle_partial_sending_failure(self):
        """
        Test what happens when there are Mailgun errors with some recipients,
        but not all.
        """
        User = get_user_model()
        User.objects.create(username="admin3",
                            email="admin1@faildomain.com",
                            is_superuser=True)

        with mock_mailgun_send_mime() as m_s:
            with mock_send_mail() as send_mail:
                handle_mail(MSG1)
                # We should have tried to send to all recipients
                self.assertEqual(m_s.call_count, 3)

                # Should have reported the error
                self.assertEqual(send_mail.call_count, 1)
                error_email = send_mail.sent_messages(0)
                self.assertIn("admin1@faildomain.com",
                              error_email.body)
                self.assertEqual(error_email.subject,
                                 "Error with email to list camp-debug@cciw.co.uk")
                self.assertEqual(error_email.to,
                                 ["Joe <joe@gmail.com>"])

    def test_users_for_address(self):
        leader_user = self.leader_user

        # non-existent
        self.assertRaises(NoSuchList,
                          lambda: users_for_address('no-such-list@cciw.co.uk',
                                                    leader_user.email))

        # camp-debug
        self.assertEqual(sorted([u.email for u in
                                 users_for_address('camp-debug@cciw.co.uk', 'anyone@gmail.com')]),
                         ['admin1@admin.com', 'admin2@admin.com'])

        # officers
        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camp-2000-blue-officers@cciw.co.uk',
                                                    'anyone@gmail.com'))

        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camp-2000-blue-officers@cciw.co.uk',
                                                    self.officer1.email))

        self.assertEqual(set(users_for_address('camp-2000-blue-officers@cciw.co.uk',
                                               leader_user.email)),
                         {self.officer1,
                          self.officer2,
                          self.officer3})

        # leaders
        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camps-2000-leaders@cciw.co.uk',
                                                    self.officer1.email))

        self.assertEqual(set(users_for_address('camps-2000-leaders@cciw.co.uk',
                                               leader_user.email)),
                         {self.leader_user})

    def test_handle_mail_permission_denied(self):
        MSG = MSG1.replace(b'camp-debug@cciw.co.uk',
                           b'camp-2000-blue-officers@cciw.co.uk')
        with mock_mailgun_send_mime() as m_s:
            with mock_send_mail() as send_mail:
                handle_mail(MSG)
                sent = m_s.messages_sent()
                self.assertEqual(len(sent), 0)
                self.assertEqual(send_mail.call_count, 1)
                self.assertIn("you do not have permission", send_mail.sent_messages(0).body)

    def test_mailgun_incoming(self):
        rf = RequestFactory()
        request = rf.post('/', data=MAILGUN_EXAMPLE_POST_DATA_FOR_MIME_ENDPOINT,
                          content_type='application/x-www-form-urlencoded')
        with mock.patch('cciw.mail.views.handle_mail') as m:
            response = views.mailgun_incoming(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(type(m.call_args[0][0]), bytes)

    def test_mailgun_incoming_bad_sig(self):
        data = MAILGUN_EXAMPLE_POST_DATA_FOR_MIME_ENDPOINT
        sig = b"d1551e3de499c753ab801d81dea14f378dbb9c369b393a16c50e50e374eceb9d"
        assert sig in data
        # one char different:
        data = data.replace(sig, b"d1551e3de499c753ab801d81dea14f378dbb9c369b393a16c50e50e374eceb9e")

        rf = RequestFactory()
        request = rf.post('/', data=data,
                          content_type='application/x-www-form-urlencoded')
        with mock.patch('cciw.mail.views.handle_mail') as m:
            response = views.mailgun_incoming(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(m.call_count, 0)

    # In test mode, we run against the sandbox account, which only has a few
    # authorized recipients. Using this, we can test both good and error conditions.
    # We then use VCR to record the interaction and make the test fast and deterministic
    @vcr.use_cassette('cciw/mail/fixtures/vcr_cassettes/send_mime_message_good.yaml')
    def test_send_mime_message_good(self):
        to = settings.MAILGUN_TEST_RECEIVER
        msg = MSG_MAILGUN_TEST.replace(b'someone@gmail.com', to.encode('utf-8'))
        response = send_mime_message(to, msg)
        self.assertIn('id', response)
        self.assertEqual(response['id'], '<56CCDE2E.9030103@gmail.com>')

    @vcr.use_cassette('cciw/mail/fixtures/vcr_cassettes/send_mime_message_error.yaml')
    def test_send_mime_message_error(self):
        to = 'someone@gmail.com'
        self.assertRaises(Exception, send_mime_message, to, MSG_MAILGUN_TEST)


def emailify(msg):
    return msg.strip().replace(b"\n", b"\r\n")


MSG1 = emailify(b"""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: Test
From: Joe <joe@gmail.com>
To: Someone <someone@gmail.com>, camp-debug@cciw.co.uk, "Someone Else" <else@gmail.com>
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@gmail.com>

Test message
""")

MSG_MAILGUN_TEST = emailify(b"""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: Test
From: website@cciw.co.uk
To: someone@gmail.com
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@gmail.com>

Test message
""")
