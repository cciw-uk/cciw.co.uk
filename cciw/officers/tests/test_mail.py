from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail

import cciw.mail.lists
from cciw.mail.lists import MailAccessDenied, NoSuchList, extract_email_addresses, handle_mail, users_for_address
from cciw.officers.email import handle_reference_bounce
from cciw.officers.tests.base import BasicSetupMixin, ExtraOfficersSetupMixin
from cciw.utils.tests.base import TestBase

User = get_user_model()

TEST_MAIL = """MIME-Version: 1.0
Date: Thu, 30 Jul 2015 10:39:10 +0100
To: "Camp 1 officers" <camp-2000-blue-officers@cciw.co.uk>
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


class MailTests(ExtraOfficersSetupMixin, TestBase):

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
        self.assertEqual(mail.outbox[0].subject, "Access to mailing list camp-2000-blue-officers@cciw.co.uk denied")

    def test_extract(self):
        self.assertEqual(extract_email_addresses('Some Guy <A.Body@example.com>'),
                         ['A.Body@example.com'])


class ReferenceBounceTest(BasicSetupMixin, TestBase):

    BOUNCE_EMAIL_GOOD = """
From - Mon May 11 21:38:48 2015
X-Account-Key: account3
X-UIDL: 1061210715.378980
X-Mozilla-Status: 0001
X-Mozilla-Status2: 00000000
X-Mozilla-Keys:                                                                                 """"""
Return-Path: <>
Received: from compute4.internal (compute4.nyi.internal [10.202.2.44])
\t by sloti33d1t06 (Cyrus 3.0-git-fastmail-10960) with LMTPA;
\t Fri, 10 Apr 2015 16:31:40 -0400
X-Sieve: CMU Sieve 2.4
X-Spam-score: 0.0
X-Spam-hits: BAYES_05 -0.5, LANGUAGES en, BAYES_USED user, SA_VERSION 3.3.2
X-Backscatter: Yes
X-Backscatter-Hosts: web178.webfaction.com, smtp.webfaction.com
X-Spam-source: IP='75.126.113.165', Host='mail7.webfaction.com', Country='US',
  FromHeader='com', MailFrom='unk'
X-Spam-charsets: plain='us-ascii'
X-Resolved-to: spookylukey@fastmail.fm
X-Delivered-to: spookylukey@fastmail.fm
X-Mail-from: """"""
Received: from mx4 ([10.202.2.203])
  by compute4.internal (LMTPProxy); Fri, 10 Apr 2015 16:31:40 -0400
Received: from mx4.messagingengine.com (localhost [127.0.0.1])
\tby mx4.nyi.internal (Postfix) with ESMTP id 374E43C010C
\tfor <spookylukey@fastmail.fm>; Fri, 10 Apr 2015 16:31:40 -0400 (EDT)
Received: from mx4.nyi.internal (localhost [127.0.0.1])
    by mx4.messagingengine.com (Authentication Milter) with ESMTP
    id 471F3F46101.1602A3C017A;
    Fri, 10 Apr 2015 16:31:40 -0400
Authentication-Results: mx4.messagingengine.com;
    dkim=none (no signatures found);
    dmarc=permerror;
    spf=none smtp.mailfrom=<>BODY=7BIT smtp.helo=hyena.aluminati.org
Received-SPF: none (<> body=7bit: No applicable sender policy available) receiver=mx4.messagingengine.com; identity=mailfrom; envelope-from="<> BODY=7BIT"; helo=hyena.aluminati.org; client-ip=64.22.123.221
Received: from hyena.aluminati.org (hyena.aluminati.org [64.22.123.221])
\tby mx4.messagingengine.com (Postfix) with ESMTP id 1602A3C017A
\tfor <spookylukey@fastmail.fm>; Fri, 10 Apr 2015 16:31:40 -0400 (EDT)
Received: from localhost (localhost [127.0.0.1])
\tby hyena.aluminati.org (Postfix) with ESMTP id C76DD22C00
\tfor <spookylukey@fastmail.fm>; Fri, 10 Apr 2015 21:31:38 +0100 (BST)
X-Quarantine-ID: <kfkN9jCgMeIY>
X-Virus-Scanned: Debian amavisd-new at hyena.aluminati.org
X-Remote-Spam-Flag: NO
X-Remote-Spam-Score: -0.508
X-Remote-Spam-Level: """"""
X-Remote-Spam-Status: No, score=-0.508 tagged_above=-9999 required=6.31
\ttests=[BAYES_00=-1.9, PYZOR_CHECK=1.392] autolearn=no
Received: from hyena.aluminati.org ([127.0.0.1])
\tby localhost (hyena.aluminati.org [127.0.0.1]) (amavisd-new, port 10024)
\twith ESMTP id kfkN9jCgMeIY for <spookylukey@fastmail.fm>;
\tFri, 10 Apr 2015 21:31:37 +0100 (BST)
Received: from mx7.webfaction.com (mail7.webfaction.com [75.126.113.165])
\tby hyena.aluminati.org (Postfix) with ESMTP id 7D33A22E95
\tfor <L.Plant.98@cantab.net>; Fri, 10 Apr 2015 21:31:36 +0100 (BST)
Received: from localhost (localhost.localdomain [127.0.0.1])
\tby mx7.webfaction.com (Postfix) with ESMTP id E163110890030
\tfor <L.Plant.98@cantab.net>; Fri, 10 Apr 2015 20:31:35 +0000 (UTC)
Received: from mx7.webfaction.com ([127.0.0.1])
\tby localhost (mail7.webfaction.com [127.0.0.1]) (amavisd-new, port 10024)
\twith ESMTP id fmMn2SZM7BMD for <L.Plant.98@cantab.net>;
\tFri, 10 Apr 2015 20:31:35 +0000 (UTC)
Received: from smtp.webfaction.com (smtp.webfaction.com [74.55.86.74])
\tby mx7.webfaction.com (Postfix) with ESMTP id 46C7F10890051
\tfor <website@cciw.co.uk>; Fri, 10 Apr 2015 20:31:35 +0000 (UTC)
Received: by smtp.webfaction.com (Postfix)
\tid 032F020F0011; Fri, 10 Apr 2015 20:31:26 +0000 (UTC)
Date: Fri, 10 Apr 2015 20:31:26 +0000 (UTC)
From: MAILER-DAEMON@smtp.webfaction.com (Mail Delivery System)
Subject: Undelivered Mail Returned to Sender
To: website@cciw.co.uk
Auto-Submitted: auto-replied
MIME-Version: 1.0
Content-Type: multipart/report; report-type=delivery-status;
\tboundary="9373720806C5.1428697886/smtp.webfaction.com"
Message-Id: <20150410203126.032F020F0011@smtp.webfaction.com>

This is a MIME-encapsulated message.

--9373720806C5.1428697886/smtp.webfaction.com
Content-Description: Notification
Content-Type: text/plain; charset=us-ascii

This is the mail system at host smtp.webfaction.com.

I'm sorry to have to inform you that your message could not
be delivered to one or more recipients. It's attached below.

For further assistance, please send mail to <postmaster>

If you do so, please include this problem report. You can
delete your own text from the attached returned message.

                   The mail system

<bobjones@xgmail.com>: Host or domain name not found. Name service error
    for name=broughtech.net type=A: Host not found

--9373720806C5.1428697886/smtp.webfaction.com
Content-Description: Delivery report
Content-Type: message/delivery-status

Reporting-MTA: dns; smtp.webfaction.com
X-Postfix-Queue-ID: 9373720806C5
X-Postfix-Sender: rfc822; website@cciw.co.uk
Arrival-Date: Fri, 10 Apr 2015 20:31:02 +0000 (UTC)

Final-Recipient: rfc822; bobjones@xgmail.com
Original-Recipient: rfc822;bobjones@xgmail.com
Action: failed
Status: 5.4.4
Diagnostic-Code: X-Postfix; Host or domain name not found. Name service error
    for name=broughtech.net type=A: Host not found

--9373720806C5.1428697886/smtp.webfaction.com
Content-Description: Undelivered Message
Content-Type: message/rfc822

Received: from web178.webfaction.com (web178.webfaction.com [75.126.149.9])
\tby smtp.webfaction.com (Postfix) with ESMTP id 9373720806C5
\tfor <bobjones@xgmail.com>; Fri, 10 Apr 2015 20:31:02 +0000 (UTC)
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: Reference Mary Morely
From: CCIW website <website@cciw.co.uk>
To: bobjones@xgmail.com
Date: Fri, 10 Apr 2015 20:31:02 -0000
Message-ID: <20150410203102.26261.51798@web178.webfaction.com>
Reply-To: joe.bloggs@hotmail.com
X-CCIW-Camp: 2000-blue

Dear Mr Bob Jones,

Mary Morely has applied to be an officer on a CCIW camp, and has put
your name down as a referee.  We would appreciate it if you could take
a few minutes to fill out a reference form online, by visiting the
following page in your web browser and filling out the form:

https://www.cciw.co.uk/officers/ref/1234--e6d29e26ccfaab24e68e/

In most e-mail programs, you should be able to click on the link
above.  If not, open up your web browser and copy and paste the whole
link into the address bar at the top of the web browser.

For those who don't enjoy writing references, please be assured that
in the future you will simply be asked to confirm or update what you
wrote this year.

Many thanks for your support of CCIW.

Joe Bloggs

For CCIW camp 1, 2015 - Joe Bloggs

--9373720806C5.1428697886/smtp.webfaction.com--
"""

    def test_forward_bounce_to_leaders(self):
        email_file = StringIO(self.BOUNCE_EMAIL_GOOD.strip())
        handle_reference_bounce(email_file)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["joe.bloggs@hotmail.com"])
        self.assertIn("was not received", m.body)
        self.assertIn("Use the following link", m.body)
