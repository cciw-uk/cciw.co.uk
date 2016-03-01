import contextlib
from unittest import mock
import smtplib

from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth import get_user_model

from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.utils.tests.base import TestBase

from .lists import MailAccessDenied, NoSuchList, handle_all_mail, handle_mail, users_for_address


def b(s):
    return bytes(s, 'ascii')


@contextlib.contextmanager
def mock_imaplib(emails_in_inbox):
    if not all(type(e) is bytes for e in emails_in_inbox):
        raise ValueError("Emails must be byte strings")
    patcher = mock.patch('imaplib.IMAP4_SSL')
    settings.IMAP_MAIL_SERVER = 'anything'
    settings.MAILBOX_PASSWORD = 'secret'

    # Basic emulation of IMAP server, with enough to
    # provide what handle_all_mail needs.
    msg_store = {b(str(i + 1)): e for i, e in enumerate(emails_in_inbox)}
    flags = {}

    with patcher as imap_class:

        def select(folder):
            if folder != "INBOX":
                raise AssertionError("Only INBOX folder supported by this mock")
            return ('OK',
                    [b(str(len(msg_store)))])

        def search(charset, criterion):
            if criterion != "ALL":
                raise AssertionError("Only ALL searches supported by this mock")

            return ('OK',
                    [b" ".join(msg_store.keys())])

        def fetch(message_set, message_parts):
            ids = message_set.split(b',')
            return ('OK',
                    [(i + b"(RFC822)",
                      msg_store[i],
                      b')')
                     for i in ids])

        def store(num, command, flag_list):
            if command == "+FLAGS":
                flags.setdefault(num, []).extend(flag_list.split(' '))
            return ('OK', [num])

        def close():
            # Messages are only really deleted by IMAP
            # servers when the connection is closed.
            for msg_id, flag_list in list(flags.items()):
                if "\\Deleted" in flag_list:
                    del msg_store[msg_id]
                    del flags[msg_id]
            return ('OK', [b'Close completed.'])

        imap_connection = imap_class()
        imap_connection.login.return_value = ('OK', [b'Logged in.'])
        imap_connection.select.side_effect = select
        imap_connection.search.side_effect = search
        imap_connection.fetch.side_effect = fetch
        imap_connection.store.side_effect = store
        imap_connection.close.side_effect = close

        # Extra helpers for test code:
        imap_connection.get_inbox = lambda: sorted(msg_store.items())

        yield imap_connection
    del settings.IMAP_MAIL_SERVER


@contextlib.contextmanager
def mock_smtplib():
    # Really just mocking an SMTP connection object, with
    # the wrapper returned by Django's 'get_connection'
    with mock.patch('cciw.mail.lists.get_connection') as get_connection:
        conn = get_connection()

        # Special behaviour:
        def sendmail(sender_addr, to_addresses, mail_bytes):
            for a in to_addresses:
                if a.endswith("@faildomain.com"):
                    raise smtplib.SMTPRecipientsRefused('"{0}" Recipient address rejected: Domain not found."'.format(a))
            # Otherwise succeed silently

        conn.connection.sendmail.side_effect = sendmail

        # Helpers for tests:
        conn.from_addresses = (
            lambda: [c[0][0] for c in conn.connection.sendmail.call_args_list])
        conn.to_addresses = (
            lambda: [c[0][1] for c in conn.connection.sendmail.call_args_list])
        conn.messages_sent = (
            lambda: [c[0][2] for c in conn.connection.sendmail.call_args_list])
        yield conn


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

    def test_handle_all_mail(self):
        with mock_imaplib([MSG1]) as m_i:
            with mock_smtplib() as m_s:
                handle_all_mail()
                self.assertEqual(m_i.fetch.call_count, 1)
                self.assertEqual(m_s.connection.sendmail.call_count, 2)
                messages_sent = m_s.messages_sent()
                to_addresses = m_s.to_addresses()
                self.assertEqual(list(sorted(to_addresses)),
                                 [["admin1@admin.com"],
                                  ["admin2@admin.com"]])
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

                self.assertEqual(len(m_i.get_inbox()), 0)

    def test_handle_all_mail_multiple(self):
        with mock_imaplib([MSG1, MSG1, MSG1]) as m_i:
            with mock_smtplib() as m_s:
                handle_all_mail()
                self.assertEqual(m_i.fetch.call_count, 3)
                self.assertEqual(m_s.connection.sendmail.call_count, 6)

    def test_handle_all_mail_smtp_connection_error(self):
        """
        Test that if an SMTP connection error occurs, the email
        is not deleted from the inbox.
        """
        with mock_imaplib([MSG1]) as m_i:
            with mock_smtplib() as m_s:
                def connection_error():
                    raise ConnectionRefusedError("Connection refused")
                m_s.open.side_effect = connection_error

                try:
                    handle_all_mail()
                except Exception:
                    pass
                self.assertEqual(len(m_i.get_inbox()), 1)

    def test_handle_partial_sending_failure(self):
        """
        Test what happens when there are SMTP errors with some recipients,
        but not all.
        """
        User = get_user_model()
        User.objects.create(username="admin3",
                            email="admin1@faildomain.com",
                            is_superuser=True)

        with mock_imaplib([MSG1]) as m_i:
            with mock_smtplib() as m_s:
                with mock_send_mail() as send_mail:
                    handle_all_mail()
                    # We should have tried to send to all recipients
                    self.assertEqual(m_s.connection.sendmail.call_count, 3)
                    # inbox should be empty
                    self.assertEqual(len(m_i.get_inbox()), 0)
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
        with mock_smtplib() as m_s:
            with mock_send_mail() as send_mail:
                handle_mail(MSG)
                sent = m_s.messages_sent()
                self.assertEqual(len(sent), 0)
                self.assertEqual(send_mail.call_count, 1)
                self.assertIn("you do not have permission", send_mail.sent_messages(0).body)


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
