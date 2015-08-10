from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase


from cciw.cciwmain.models import Camp
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.officers.tests.base import ExtraOfficersSetupMixin

from cciw.mail.lists import users_for_address, NoSuchList, handle_mail
import cciw.mail.lists


TEST_MAIL = """MIME-Version: 1.0
Date: Thu, 30 Jul 2015 10:39:10 +0100
To: camp-2000-1-officers@cciw.co.uk
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

    def test_officer_list(self):
        self.assertRaises(NoSuchList,
                          lambda: users_for_address('camp-2000-1-officers@cciw.co.uk', 'joe@random.com'))

        l1 = users_for_address('camp-2000-1-officers@cciw.co.uk', 'LEADER@SOMEWHERE.COM')

        self.assertEqual([u.username for u in l1],
                         ["fredjones", "joebloggs", "petersmith"])

    def test_leader_list(self):
        # Check perms:

        # non-priviliged user:
        u = User.objects.create(username="joerandom", email="joe@random.com", is_superuser=False)
        self.assertRaises(NoSuchList,
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
        connection = DummyConnection()
        backend = DummyBackend(connection)
        get_connection = lambda name: backend
        cciw.mail.lists.get_connection = get_connection

        self.assertEqual(connection.sent, [])
        handle_mail(TEST_MAIL)
        self.assertEqual(len(connection.sent), 3)

        self.assertTrue(all(f == 'Dave Stott <leader@somewhere.com>' for f, t, m in connection.sent))
        self.assertEqual(connection.sent[0][1][0], '"Fred Jones" <fredjones@somewhere.com>')
        self.assertIn("Sender: CCIW lists".encode('utf-8'), connection.sent[0][2])
        self.assertIn("From: Dave Stott <leader@somewhere.com>".encode('utf-8'), connection.sent[0][2])
