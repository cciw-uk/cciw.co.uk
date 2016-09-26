from django.contrib.auth import get_user_model
from django.core import mail

from cciw.mail.lists import MailAccessDenied, NoSuchList, extract_email_addresses, handle_mail, users_for_address
from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.utils.tests.base import TestBase
from cciw.mail.tests import mock_mailgun_send_mime

User = get_user_model()

TEST_MAIL = """MIME-Version: 1.0
Date: Thu, 30 Jul 2015 10:39:10 +0100
To: "Camp 1 officers" <camp-2000-blue-officers@cciw.co.uk>
Subject: Minibus Drivers
Content-Type: text/plain; charset="us-ascii"
From: Dave Stott <leader@somewhere.com>
Content-Type: text/plain; charset=utf-8

This is a message!

"""


class DummyConnection(object):
    def __init__(self):
        self.sent = []

    def sendmail(self, *args):
        self.sent.append(args)


class DummyBackend(object):
    def __init__(self, connection):
        self.connection = connection

    def open(self):
        pass

    def close(self):
        pass


class MailTests(ExtraOfficersSetupMixin, TestBase):

    def test_invalid_list(self):
        self.assertRaises(NoSuchList,
                          lambda: users_for_address('everyone@cciw.co.uk', 'joe@random.com'))
        self.assertRaises(NoSuchList,
                          lambda: users_for_address('x-camp-2000-blue-officers@cciw.co.uk', 'joe@random.com'))

    def test_officer_list(self):
        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camp-2000-blue-officers@cciw.co.uk', 'joe@random.com'))

        l1 = users_for_address('camp-2000-blue-officers@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        self.assertEqual([u.username for u in l1],
                         ["fredjones", "joebloggs", "petersmith"])

    def test_leader_list(self):
        # Check perms:

        # non-priviliged user:
        user = User.objects.create(username="joerandom", email="joe@random.com", is_superuser=False)
        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camp-2000-blue-leaders@cciw.co.uk', 'joe@random.com'))

        # superuser:
        user.is_superuser = True
        user.save()
        l1 = users_for_address('camp-2000-blue-leaders@cciw.co.uk', 'JOE@RANDOM.COM')

        # leader:
        l2 = users_for_address('camp-2000-blue-leaders@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        # Check contents
        self.assertEqual([u.username for u in l1],
                         ["davestott"])

        self.assertEqual(l1, l2)

    def test_handle(self):
        with mock_mailgun_send_mime() as m_s:
            handle_mail(TEST_MAIL)

        sent_messages = m_s.messages_sent()
        self.assertEqual(len(sent_messages), 3)

        self.assertTrue(all(b'From: Dave Stott <leader@somewhere.com>' in m for m in sent_messages))
        self.assertEqual(m_s.call_args_list[0][0][0], '"Fred Jones" <fredjones@somewhere.com>')
        self.assertIn(b"Sender: CCIW lists", sent_messages[0])
        self.assertIn(b"From: Dave Stott <leader@somewhere.com>", sent_messages[0])

    def test_handle_bounce(self):
        bad_mail = TEST_MAIL.replace("leader@somewhere.com", "notleader@somewhere.com")
        with mock_mailgun_send_mime() as m_s:
            handle_mail(bad_mail)
        self.assertEqual(m_s.messages_sent(), [])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Access to mailing list camp-2000-blue-officers@cciw.co.uk denied")

    def test_extract(self):
        self.assertEqual(extract_email_addresses('Some Guy <A.Body@example.com>'),
                         ['A.Body@example.com'])
