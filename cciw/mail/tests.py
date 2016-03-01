import contextlib
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model

from cciw.utils.tests.base import TestBase

from .lists import handle_all_mail


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
            for msg_id, flag_list in flags.items():
                if "\\Deleted" in flag_list:
                    del msg_store[msg_id]
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
    patcher = mock.patch('cciw.mail.lists.get_connection')
    with patcher as get_connection:
        conn = get_connection()
        # Helpers
        conn.from_addresses = (
            lambda: [c[0][0] for c in conn.connection.sendmail.call_args_list])
        conn.to_addresses = (
            lambda: [c[0][1] for c in conn.connection.sendmail.call_args_list])
        conn.messages_sent = (
            lambda: [c[0][2] for c in conn.connection.sendmail.call_args_list])
        yield conn


class TestMailingLists(TestBase):

    def test_handle_all_mail(self):
        User = get_user_model()
        User.objects.all().delete()
        User.objects.create(username="admin1",
                            email="admin1@admin.com",
                            is_superuser=True)
        User.objects.create(username="admin2",
                            email="admin2@admin.com",
                            is_superuser=True)

        with mock_imaplib([MSG1]) as m1:
            with mock_smtplib() as m2:
                handle_all_mail()
                self.assertEqual(m1.fetch.call_count, 1)
                self.assertEqual(m2.connection.sendmail.call_count, 2)
                messages_sent = m2.messages_sent()
                to_addresses = m2.to_addresses()
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

                self.assertEqual(len(m1.get_inbox()), 0)


def emailify(msg):
    return msg.strip().replace(b"\n", b"\r\n")


MSG1 = emailify(b"""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: Test
From: Joe <joe@gmail.com>
To: camp-debug@cciw.co.uk
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@gmail.com>

Test message
""")
