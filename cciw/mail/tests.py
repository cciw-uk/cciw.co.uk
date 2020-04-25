import re
from unittest import mock

import mailer.engine
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.test.client import RequestFactory
from django.test.utils import override_settings
from mailer.models import Message
from requests.exceptions import ConnectionError

from cciw.accounts.models import COMMITTEE_GROUP_NAME
from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.utils.functional import partition
from cciw.utils.tests.base import TestBase

from . import views
from .lists import MailAccessDenied, NoSuchList, extract_email_addresses, find_list, handle_mail, mangle_from_address
from .test_data import (MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT,
                        MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT_CONTENT_TYPE,
                        MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT_FOR_REFERENCE,
                        MAILGUN_EXAMPLE_POST_DATA_FOR_MIME_ENDPOINT)

User = get_user_model()


def b(s):
    return bytes(s, 'ascii')


def partition_mailing_list_rejections(messages):
    return partition(lambda m: re.match(r'\[CCIW\] Access to mailing list .* denied', m.subject), messages)


class TestMailingLists(ExtraOfficersSetupMixin, TestBase):
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
                          lambda: find_list('everyone@cciw.co.uk', 'joe@random.com'))
        self.assertRaises(NoSuchList,
                          lambda: find_list('x-camp-2000-blue-officers@cciw.co.uk', 'joe@random.com'))

    def test_officer_list(self):
        self.assertRaises(MailAccessDenied,
                          lambda: find_list('camp-2000-blue-officers@cciw.co.uk',
                                            'joe@random.com'))

        self.assertRaises(MailAccessDenied,
                          lambda: find_list('camp-2000-blue-officers@cciw.co.uk',
                                            self.officer1.email))

        officer_list = find_list('camp-2000-blue-officers@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        self.assertEqual([u.username for u in officer_list.members],
                         ["fredjones", "joebloggs", "petersmith"])

    def test_debug_list(self):
        self.assertEqual(sorted([u.email for u in
                                 find_list('camp-debug@cciw.co.uk', 'anyone@gmail.com').members]),
                         ['admin1@admin.com', 'admin2@admin.com'])

    def test_leader_list(self):
        leader_user = self.leader_user

        # Permissions

        # Officer/non-privileged
        self.assertRaises(MailAccessDenied,
                          lambda: find_list('camps-2000-leaders@cciw.co.uk',
                                            self.officer1.email))

        # superuser:
        l1 = find_list('camp-2000-blue-leaders@cciw.co.uk', 'ADMIN1@ADMIN.COM')

        # leader:
        l2 = find_list('camp-2000-blue-leaders@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        # DBS officer
        l3 = find_list('camp-2000-blue-leaders@cciw.co.uk', 'DBSOFFICER@somewhere.com')

        # Contents
        members = set(find_list('camps-2000-leaders@cciw.co.uk',
                                leader_user.email).members)
        self.assertEqual(members,
                         {self.leader_user})

        self.assertEqual(l1, l2)
        self.assertEqual(l1, l3)

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

    def test_handle_committee_list(self):
        committee, _ = Group.objects.get_or_create(name=COMMITTEE_GROUP_NAME)
        committee.user_set.create(
            username="aman1",
            email="a.man@example.com")
        committee.user_set.create(
            username="awoman1",
            email="a.woman@example.com")

        # Email address without permission
        msg = MSG_COMMITTEE_LIST.replace(b'a.woman@example.com', b'joe@gmail.com')
        handle_mail(msg)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(rejections), 1)
        self.assertEqual(len(sent_messages), 0)

        # Email address without permission
        handle_mail(MSG_COMMITTEE_LIST)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]
        sent_to_addresses = list(sorted([address for m in sent_messages for address in m.recipients()]))
        self.assertEqual(sent_to_addresses,
                         ["a.man@example.com",
                          "a.woman@example.com"])
        self.assertTrue(all(b"Sender: committee@cciw.co.uk" in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(b"List-Post: <mailto:committee@cciw.co.uk>" in m
                            for m in sent_messages_bytes))

    def test_handle_officer_list(self):
        handle_mail(MSG_OFFICER_LIST)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(rejections), 0)
        self.assertEqual(len(sent_messages), 3)

        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]

        self.assertTrue(all(b'\nX-Original-From: Dave Stott <leader@somewhere.com>' in m
                            for m in sent_messages_bytes))
        self.assertTrue(all(m.from_email == 'Dave Stott leader(at)somewhere.com via <noreply@cciw.co.uk>'
                            for m in sent_messages))
        self.assertTrue(all(b"Sender: CCIW website <noreply@cciw.co.uk>" in m
                            for m in sent_messages_bytes))
        self.assertTrue(any(True for m in mail.outbox if '"Fred Jones" <fredjones@somewhere.com>' in m.to))

    def test_extract(self):
        self.assertEqual(extract_email_addresses('Some Guy <A.Body@example.com>'),
                         ['A.Body@example.com'])

    def test_handle_mail_exception(self):
        """
        Test that if an error always occurs trying to send, handle_mail raises
        Exception. (This means that mailgun_incoming will return
        a 500, and Mailgun will attempt to POST again)
        """
        with mock.patch('cciw.mail.lists.send_mime_message') as m_s:
            def connection_error():
                raise ConnectionError("Connection refused")
            m_s.side_effect = connection_error
            self.assertRaises(Exception, handle_mail, MSG_DEBUG_LIST)

    def test_handle_invalid_list(self):
        msg = MSG_DEBUG_LIST.replace(b'camp-debug@cciw.co.uk',
                                     b'camp-1990-blue-officers@cciw.co.uk')
        handle_mail(msg)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(len(sent_messages), 0)
        self.assertEqual(len(rejections), 1)
        error_email = rejections[0]
        self.assertIn('camp-1990-blue-officers@cciw.co.uk',
                      error_email.body)
        self.assertIn('list does not exist',
                      error_email.body)

    def test_handle_partial_sending_failure(self):
        """
        Test what happens when there are SMTP errors with some recipients,
        but not all.
        """
        User = get_user_model()
        User.objects.create(username="admin3",
                            email="admin1@faildomain.com",
                            is_superuser=True)

        with mock.patch('cciw.mail.lists.send_mime_message') as m_s:
            def sendmail(to_address, from_address, mail_bytes):
                if to_address.endswith("@faildomain.com"):
                    raise Exception("We don't like {0}!".format(to_address))
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
                         "[CCIW] Error with email to list camp-debug@cciw.co.uk")
        self.assertEqual(error_email.to,
                         ["Joe <joe@gmail.com>"])

    def test_handle_mail_permission_denied(self):
        bad_mail = MSG_OFFICER_LIST.replace(b"leader@somewhere.com",
                                            b"joe@gmail.com")
        handle_mail(bad_mail)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        self.assertEqual(sent_messages, [])
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0].subject, "[CCIW] Access to mailing list camp-2000-blue-officers@cciw.co.uk denied")
        self.assertIn("you do not have permission", rejections[0].body)

    def test_handle_mail_permission_denied_for_unknown(self):
        bad_mail = MSG_OFFICER_LIST.replace(b"leader@somewhere.com", b"randomer@random.com")
        handle_mail(bad_mail)
        self.assertEqual(len(mail.outbox), 0)

    def test_mailgun_incoming(self):
        rf = RequestFactory()
        request = rf.post('/', data=MAILGUN_EXAMPLE_POST_DATA_FOR_MIME_ENDPOINT,
                          content_type='application/x-www-form-urlencoded')
        with mock.patch('cciw.mail.views.handle_mail_async') as m:
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
        with mock.patch('cciw.mail.views.handle_mail_async') as m:
            response = views.mailgun_incoming(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(m.call_count, 0)

    def test_mailgun_bounce(self):
        rf = RequestFactory()
        request = rf.post('/', data=MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT,
                          content_type=MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT_CONTENT_TYPE)
        with mock.patch('cciw.officers.email.handle_reference_bounce') as m:
            response = views.mailgun_bounce_notification(request)
        self.assertEqual(m.call_count, 0)
        self.assertEqual(response.status_code, 200)

    def test_mailgun_bounce_for_reference(self):
        rf = RequestFactory()
        request = rf.post('/', data=MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT_FOR_REFERENCE,
                          content_type=MAILGUN_EXAMPLE_POST_DATA_FOR_BOUNCE_ENDPOINT_CONTENT_TYPE)
        response = views.mailgun_bounce_notification(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["joe.bloggs@hotmail.com"])
        self.assertIn("was not received", m.body)
        self.assertIn("sent to bobjones@xgmail.com", m.body)
        self.assertIn("Use the following link", m.body)

        # Check that we can serialise
        m.message().as_bytes()

        # Check the attachment
        attachment = m.attachments[0]
        self.assertIn(b'Hi Bob, Please do a reference.', attachment.as_bytes())

    def test_mangle_from_address(self):
        self.assertEqual(mangle_from_address("foo@bar.com"),
                         "foo(at)bar.com via <noreply@cciw.co.uk>")
        self.assertEqual(mangle_from_address("Mr Foo <foo@bar.com>"),
                         "Mr Foo foo(at)bar.com via <noreply@cciw.co.uk>")


def emailify(msg):
    return msg.strip().replace("\n", "\r\n").encode('utf-8')


_EMAIL_SENDING_DISALLOWED = []


def disable_email_sending():
    _EMAIL_SENDING_DISALLOWED.append(None)


def enable_email_sending():
    _EMAIL_SENDING_DISALLOWED.pop(0)


# Most mail is sent directly, but some is specifically put on a queue, to ensure
# errors don't mess up payment processing. We 'send' and retrieve those here:
def send_queued_mail():
    len_outbox_start = len(mail.outbox)
    sent_count = Message.objects.all().count()
    # mailer itself uses transactions for sending, triggering our AtomicChecksMixin
    # logic and disabling email sending using TestMailBackend:
    with override_settings(MAILER_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
        mailer.engine.send_all()
    len_outbox_end = len(mail.outbox)
    assert len_outbox_start + sent_count == len_outbox_end, \
        "Expected {0} + {1} == {2}".format(len_outbox_start, sent_count, len_outbox_end)
    sent = mail.outbox[len_outbox_start:]
    mail.outbox[len_outbox_start:] = []
    assert len(mail.outbox) == len_outbox_start
    return sent


class TestMailBackend(LocMemEmailBackend):

    def send_messages(self, messages):
        # Transaction check
        if len(_EMAIL_SENDING_DISALLOWED) > 0:
            raise AssertionError("Normal email should not be sent within transactions, "
                                 "use queued_mail instead")

        # Subject check
        for m in messages:
            if (not m.subject.startswith('[CCIW]') and
                    b' via <noreply@cciw.co.uk>' not in m.message().as_bytes()):
                raise AssertionError("Email with subject \"{0}\" should start with [CCIW]"
                                     .format(m.subject))

        return super(TestMailBackend, self).send_messages(messages)


MSG_DEBUG_LIST = emailify("""
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

MSG_COMMITTEE_LIST = (MSG_DEBUG_LIST
                      .replace(b'camp-debug@cciw.co.uk', b'committee@cciw.co.uk')
                      .replace(b'joe@gmail.com', b'a.woman@example.com')
                      )

MSG_OFFICER_LIST = emailify("""
MIME-Version: 1.0
Date: Thu, 30 Jul 2015 10:39:10 +0100
To: "Camp 1 officers" <camp-2000-blue-officers@cciw.co.uk>
Subject: Minibus Drivers
Content-Type: text/plain; charset="us-ascii"
From: Dave Stott <leader@somewhere.com>
Content-Type: text/plain; charset=utf-8

This is a message!

""")

MSG_MAILGUN_TEST = emailify("""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: Test
From: noreply@cciw.co.uk
To: someone@gmail.com
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@gmail.com>

Test message
""")
