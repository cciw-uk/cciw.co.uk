from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase


from cciw.cciwmain.models import Camp
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.officers.tests.base import ExtraOfficersSetupMixin

from cciw.mail.lists import users_for_address, NoSuchList, MailAccessDenied, handle_mail, extract_email_addresses
import cciw.mail.lists


User = get_user_model()

TEST_MAIL = """MIME-Version: 1.0
Date: Thu, 30 Jul 2015 10:39:10 +0100
To: "Camp 1 officers" <camp-2000-1-officers@cciw.co.uk>
Subject: Minibus Drivers
Content-Type: text/plain; charset="us-ascii"
From: Dave Stott <leader@somewhere.com>
Content-Type: text/plain; charset=utf-8

This is a message!

""".encode('utf-8')


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


class MailTests(ExtraOfficersSetupMixin, TestCase):

    def setUp(self):
        super(MailTests, self).setUp()
        connection = DummyConnection()
        backend = DummyBackend(connection)
        get_connection = lambda name: backend
        cciw.mail.lists.get_connection = get_connection
        self.connection = connection

    def test_invalid_list(self):
        self.assertRaises(NoSuchList,
                          lambda: users_for_address('committee@cciw.co.uk', 'joe@random.com'))
        self.assertRaises(NoSuchList,
                          lambda: users_for_address('x-camp-2000-1-officers@cciw.co.uk', 'joe@random.com'))

    def test_officer_list(self):
        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camp-2000-1-officers@cciw.co.uk', 'joe@random.com'))

        l1 = users_for_address('camp-2000-1-officers@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        self.assertEqual([u.username for u in l1],
                         ["fredjones", "joebloggs", "petersmith"])

    def test_leader_list(self):
        # Check perms:

        # non-priviliged user:
        u = User.objects.create(username="joerandom", email="joe@random.com", is_superuser=False)
        self.assertRaises(MailAccessDenied,
                          lambda: users_for_address('camp-2000-1-leaders@cciw.co.uk', 'joe@random.com'))

        # superuser:
        u.is_superuser = True
        u.save()
        l1 = users_for_address('camp-2000-1-leaders@cciw.co.uk', 'JOE@RANDOM.COM')

        # leader:
        l2 = users_for_address('camp-2000-1-leaders@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        # Check contents
        self.assertEqual([u.username for u in l1],
                         ["davestott"])

        self.assertEqual(l1, l2)

    def test_handle(self):
        connection = self.connection
        self.assertEqual(connection.sent, [])
        handle_mail(TEST_MAIL)
        self.assertEqual(len(connection.sent), 3)

        self.assertTrue(all(b'From: Dave Stott <leader@somewhere.com>' in m for f, t, m in connection.sent))
        self.assertEqual(connection.sent[0][1][0], '"Fred Jones" <fredjones@somewhere.com>')
        self.assertIn(b"Sender: CCIW lists", connection.sent[0][2])
        self.assertIn(b"From: Dave Stott <leader@somewhere.com>", connection.sent[0][2])

    def test_handle_bounce(self):
        bad_mail = TEST_MAIL.replace(b"leader@somewhere.com", b"notleader@somewhere.com")
        handle_mail(bad_mail)
        self.assertEqual(self.connection.sent, [])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Access to mailing list camp-2000-1-officers@cciw.co.uk denied")

    def test_extract(self):
        self.assertEqual(extract_email_addresses('Some Guy <A.Body@example.com>'),
                         ['A.Body@example.com'])
