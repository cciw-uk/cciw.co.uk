import email
import re
from email import policy
from unittest import mock

import mailer as queued_mail
import mailer.engine
import pytest
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.db.transaction import atomic
from django.test.client import RequestFactory
from django.test.utils import override_settings
from requests.exceptions import ConnectionError

from cciw.accounts.models import Role, User
from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.tests import factories as officer_factories
from cciw.officers.tests.base import RolesSetupMixin
from cciw.utils.functional import partition
from cciw.utils.tests.base import AtomicChecksMixin, TestBase

from . import views
from .lists import MailAccessDenied, NoSuchList, extract_email_addresses, find_list, handle_mail, mangle_from_address
from .test_data import AWS_BOUNCE_NOTIFICATION, AWS_MESSAGE_ID, AWS_SNS_NOTIFICATION, BAD_MESSAGE_1


def b(s):
    return bytes(s, "ascii")


def partition_mailing_list_rejections(messages):
    return partition(lambda m: re.match(r"\[CCIW\] Access to mailing list .* denied", m.subject), messages)


class TestMailingLists(RolesSetupMixin, TestBase):
    # Tests for mailing list sending. Note that because we are forwarding on raw
    # MIME objects with minimal changes, we are using
    # cciw.mail.smtp.RawEmailMessage, and that means we have to test most things
    # about messages using `email.message().as_bytes()`

    def test_invalid_list(self):
        camp_factories.create_camp(camp_name="Blue", year=2000)
        with pytest.raises(NoSuchList):
            find_list("everyone@mailtest.cciw.co.uk", "joe@random.com")
        with pytest.raises(NoSuchList):
            find_list("x-camp-2000-blue-officers@mailtest.cciw.co.uk", "joe@random.com")
        with pytest.raises(NoSuchList):
            find_list("camp-2000-neon-officers@mailtest.cciw.co.uk", "joe@random.com")

    def test_officer_list(self):
        camp_factories.create_camp(
            camp_name="Blue",
            year=2000,
            leader=(leader := officer_factories.create_officer()),
            officers=[(officer := officer_factories.create_officer())],
        )
        with pytest.raises(MailAccessDenied):
            find_list("camp-2000-blue-officers@mailtest.cciw.co.uk", "joe@random.com")

        with pytest.raises(MailAccessDenied):
            find_list("camp-2000-blue-officers@mailtest.cciw.co.uk", officer.email)

        for email_address in (leader.email.upper(), leader.email.lower()):
            officer_list = find_list("camp-2000-blue-officers@mailtest.cciw.co.uk", email_address)
            assert list(officer_list.get_members()) == [officer]

    def test_leader_lists(self):
        camp = camp_factories.create_camp(year=2020, camp_name="Blue")
        (_, leader_1_user), (_, leader_2_user) = camp_factories.create_and_add_leaders(
            camp, count=2, email_template="leader{n}@example.com"
        )
        officer_factories.add_officers_to_camp(camp, [officer := officer_factories.create_officer()])

        camp_2 = camp_factories.create_camp(year=2020, camp_name="Red")
        ((_, leader_3_user),) = camp_factories.create_and_add_leaders(
            camp_2, count=1, username_template="other_leader", email_template="other_leader@example.com"
        )

        # Add an existing leader to a second camp
        camp_factories.add_camp_leader(camp, leader_1_user)

        # Permissions

        # Officer/non-privileged
        with pytest.raises(MailAccessDenied):
            find_list("camps-2020-leaders@mailtest.cciw.co.uk", officer.email)

        # superuser:
        superuser = officer_factories.create_officer(is_superuser=True)
        l1 = find_list("camp-2020-blue-leaders@mailtest.cciw.co.uk", superuser.email)

        # leader:
        l2 = find_list("camp-2020-blue-leaders@mailtest.cciw.co.uk", leader_1_user.email)

        # DBS officer
        dbs_officer = officer_factories.create_dbs_officer()
        l3 = find_list("camp-2020-blue-leaders@mailtest.cciw.co.uk", dbs_officer.email.upper())

        # Contents
        expected_members = {leader_1_user, leader_2_user}

        for email_list in [l1, l2, l3]:
            assert email_list.get_members() == expected_members
            assert email_list.address == "camp-2020-blue-leaders@mailtest.cciw.co.uk"

        # All leader list
        l4 = find_list("camps-2020-leaders@mailtest.cciw.co.uk", leader_1_user.email)
        members = l4.get_members()
        assert members == [leader_1_user, leader_2_user, leader_3_user]

    def _setup_role_for_email(self, *, name="Test", email, allow_emails_from_public, recipients):
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
            email="committee@mailtest.cciw.co.uk",
            recipients=[("aperson1", "a.person.1@example.com"), ("aperson2", "a.person.2@example.com")],
        )
        other_user = User.objects.create(username="joe", email="joe@example.com")

        # Email address without permission
        msg1 = make_message(to_email=role.email, from_email=other_user.email)
        handle_mail(msg1)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 1
        assert len(sent_messages) == 0

        # Email address with permission
        msg2 = make_message(
            to_email=role.email,
            from_email="Me <a.person.1@example.com>",
        )
        handle_mail(msg2)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 1
        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]
        sent_to_addresses = list(sorted(address for m in sent_messages for address in m.recipients()))
        assert sent_to_addresses == [
            "a.person.1@example.com",
            "a.person.2@example.com",
        ]
        assert all(b"Sender: committee@mailtest.cciw.co.uk" in m for m in sent_messages_bytes)
        assert all(b"List-Post: <mailto:committee@mailtest.cciw.co.uk>" in m for m in sent_messages_bytes)
        assert all(m.from_email == '"Me a.person.1(at)example.com" <noreply@cciw.co.uk>' for m in sent_messages)
        assert all(b"\nX-Original-From: Me <a.person.1@example.com>" in m for m in sent_messages_bytes)
        assert all(b"Subject: Test" in m for m in sent_messages_bytes)
        assert all(b"X-Original-To: committee@mailtest.cciw.co.uk" in m for m in sent_messages_bytes)

        # With current implementation, we send just one email
        assert len(sent_messages) == 1

    def test_handle_public_role_list(self):
        role = self._setup_role_for_email(
            email="myrole@mailtest.cciw.co.uk",
            allow_emails_from_public=True,
            recipients=[("test1", "test1@example.com")],
        )

        # Email address without membership
        msg = make_message(to_email=role.email, from_email="someone@example.com")
        handle_mail(msg)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 0
        assert len(sent_messages) == 1
        sent_to_addresses = list(sorted(address for m in sent_messages for address in m.recipients()))
        assert sent_to_addresses == ["test1@example.com"]

        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]
        assert not any(b"List-Post: <mailto:myrole@mailtest.cciw.co.uk>" in m for m in sent_messages_bytes)

    def test_handle_internationalised_headers(self):
        role = self._setup_role_for_email(
            email="myrole@mailtest.cciw.co.uk",
            allow_emails_from_public=True,
            recipients=[("test1", "test1@example.com")],
        )

        msg = make_message(to_email=role.email, from_email="Çelik <celik@example.com>")
        handle_mail(msg)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 0
        assert len(sent_messages) == 1

        sent_message_parsed = email.message_from_bytes(sent_messages[0].message().as_bytes(), policy=policy.SMTP)
        assert sent_message_parsed["From"] == '"Çelik celik(at)example.com" <noreply@cciw.co.uk>'

    def test_handle_bad_message_malformed_1(self):
        msg = emailify(BAD_MESSAGE_1)
        handle_mail(msg)

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 0
        assert len(sent_messages) == 0

    def test_handle_officer_list(self):
        camp = camp_factories.create_camp(
            year=2000,
            camp_name="Pink",
            leader=officer_factories.create_officer(email=(leader_email := "kevin.smith@example.com")),
        )
        officer_factories.add_officers_to_camp(
            camp,
            [
                officer_factories.create_officer(
                    first_name="Fred",
                    last_name="Jones",
                    email="fredjones@example.com",
                ),
                officer_factories.create_officer(),
                officer_factories.create_officer(),
            ],
        )
        handle_mail(
            make_message(
                from_email=f"Kevin Smith <{leader_email}>",
                to_email="camp-2000-pink-officers@mailtest.cciw.co.uk",
            )
        )

        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(rejections) == 0
        assert len(sent_messages) == 3

        sent_messages_bytes = [m.message().as_bytes() for m in sent_messages]

        assert all(b"\nX-Original-From: Kevin Smith <kevin.smith@example.com>" in m for m in sent_messages_bytes)
        assert all(
            m.from_email == '"Kevin Smith kevin.smith(at)example.com" <noreply@cciw.co.uk>' for m in sent_messages
        )
        assert all(b"Sender: CCIW website <noreply@cciw.co.uk>" in m for m in sent_messages_bytes)
        assert any(True for m in mail.outbox if '"Fred Jones" <fredjones@example.com>' in m.to)

    def test_spam_and_virus_checking(self):
        role = self._setup_role_for_email(
            name="Test",
            email="test@mailtest.cciw.co.uk",
            allow_emails_from_public=True,
            recipients=[("test", "test@example.com")],
        )
        for header in ["X-SES-Spam-Verdict: FAIL", "X-SES-Virus-Verdict: FAIL"]:
            msg = make_message(to_email=role.email, additional_headers=[header])
            handle_mail(msg)
            rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
            assert rejections == []
            assert sent_messages == []

    def test_extract(self):
        assert extract_email_addresses("Some Guy <A.Body@example.com>") == ["A.Body@example.com"]

    def test_handle_mail_exception(self):
        """
        Test that if an error always occurs trying to send, handle_mail raises
        Exception. (This means that we will get error logs about it.)
        """
        role = self._setup_role_for_email(
            allow_emails_from_public=False,
            email="committee@mailtest.cciw.co.uk",
            recipients=[("aperson", "a.person@example.com")],
        )
        with mock.patch("cciw.mail.lists.send_mime_message") as m_s:

            def connection_error():
                raise ConnectionError("Connection refused")

            m_s.side_effect = connection_error
            with pytest.raises(Exception):
                handle_mail(
                    make_message(to_email=role.email, from_email="a.person@example.com"),
                )

    def test_handle_invalid_list(self):
        msg = make_message(to_email="camp-1990-blue-officers@mailtest.cciw.co.uk")
        handle_mail(msg)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert len(sent_messages) == 0
        assert len(rejections) == 0

    def test_handle_partial_sending_failure(self):
        """
        Test what happens when there are SMTP errors with some recipients,
        but not all.
        """
        role = self._setup_role_for_email(
            allow_emails_from_public=True,  # not a 'reply all' list
            email="committee@mailtest.cciw.co.uk",
            recipients=[
                ("aperson1", "a.person.1@example.com"),
                ("aperson2", "a.person.2@example.com"),
                ("person", "person@faildomain.com"),
            ],
        )

        with mock.patch("cciw.mail.lists.send_mime_message") as m_s:

            def sendmail(to_addresses, from_address, mail_bytes):
                for to_address in to_addresses:
                    if to_address.endswith("@faildomain.com"):
                        raise Exception(f"We don't like {to_address}!")
                # Otherwise succeed silently

            m_s.side_effect = sendmail

            handle_mail(make_message(to_email=role.email, from_email="a.person.1@example.com"))
        # We should have tried to send to all recipients
        assert m_s.call_count == 3

        # Should have reported the error
        assert len(mail.outbox) == 1
        error_email = mail.outbox[0]
        assert "person@faildomain.com" in error_email.body
        assert error_email.subject == "[CCIW] Error with email to list committee@mailtest.cciw.co.uk"
        assert error_email.to == ["a.person.1@example.com"]

    def test_handle_mail_permission_denied(self):
        camp_factories.create_camp(year=2000, camp_name="Orange")
        officer_factories.create_officer(email="other.officer@example.com")
        bad_mail = make_message(
            to_email="camp-2000-orange-officers@mailtest.cciw.co.uk",
            from_email="Other Person <other.officer@example.com>",
            subject="🍊 Orange camp 2000 🍊",
        )
        handle_mail(bad_mail)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert sent_messages == []
        assert len(rejections) == 1
        assert (
            rejections[0].subject
            == "[CCIW] Access to mailing list camp-2000-orange-officers@mailtest.cciw.co.uk denied"
        )
        body = rejections[0].body
        assert "you do not have permission" in body
        assert "🍊 Orange camp 2000 🍊" in body

    def test_handle_mail_permission_denied_for_unknown(self):
        camp_factories.create_camp(year=2000, camp_name="Pink")
        bad_mail = make_message(
            to_email="camp-2000-pink-officers@mailtest.cciw.co.uk",
            from_email="randomer@random.com",
        )
        handle_mail(bad_mail)
        assert len(mail.outbox) == 0

    def test_ses_incoming(self):
        request = make_plain_text_request("/", AWS_SNS_NOTIFICATION["body"], AWS_SNS_NOTIFICATION["headers"])
        with (
            mock.patch("cciw.aws.verify_sns_notification") as m1,
            mock.patch("cciw.mail.views.handle_mail_from_s3_async") as m2,
        ):
            m1.side_effect = [True]  # fake verify
            response = views.ses_incoming_notification(request)

        assert response.status_code == 200
        assert m1.call_count == 1
        assert m2.call_count == 1
        assert m2.call_args[0][0] == AWS_MESSAGE_ID.decode("ascii")

    # TODO it would be nice to have tests for cciw/aws.py functions,
    # to ensure no regressions.

    def test_ses_bounce_for_reference(self):
        camp_factories.create_camp(camp_name="Blue", year=2000)  # Matches X-CCIW-Camp header below
        request = make_plain_text_request("/", AWS_BOUNCE_NOTIFICATION["body"], AWS_BOUNCE_NOTIFICATION["headers"])
        with mock.patch("cciw.aws.verify_sns_notification") as m1:
            m1.side_effect = [True]  # fake verify
            response = views.ses_bounce_notification(request)

        assert response.status_code == 200
        assert m1.call_count == 1

        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert m.to == ["a.camp.leader@example.com"]
        assert "was not received" in m.body
        assert "sent to a.referrer@example.com" in m.body
        assert "Use the following link" in m.body
        assert response.status_code == 200

    def test_mangle_from_address(self):
        assert mangle_from_address("foo@bar.com") == '"foo(at)bar.com" <noreply@cciw.co.uk>'
        assert mangle_from_address("Mr Foo <foo@bar.com>") == '"Mr Foo foo(at)bar.com" <noreply@cciw.co.uk>'

    def test_invalid_characters(self):
        bad_mail = MSG_BAD_CHARACTERS
        handle_mail(bad_mail)
        rejections, sent_messages = partition_mailing_list_rejections(mail.outbox)
        assert sent_messages == []
        assert rejections == []


def emailify(msg):
    return msg.strip().replace("\n", "\r\n").encode("utf-8")


_NON_QUEUED_EMAIL_SENDING_DISALLOWED = []


def disable_nonqueued_email_sending():
    _NON_QUEUED_EMAIL_SENDING_DISALLOWED.append(None)


def enable_nonqueued_email_sending():
    _NON_QUEUED_EMAIL_SENDING_DISALLOWED.pop(0)


# Most mail is sent directly, but some is specifically put on a queue, to ensure
# errors don't mess up payment processing. We 'send' and retrieve those here:
def send_queued_mail() -> list[mail.EmailMessage]:
    # mailer itself uses transactions for sending. Normally it runs in a
    # separate process, but in tests we run it in process, which would trigger
    # our AtomicChecksMixin logic. This means we can't do
    # `MAILER_EMAIL_BACKEND=TestMailBackend`, so we use
    # `QueuedMailTestEmailBackend`
    with override_settings(MAILER_EMAIL_BACKEND="cciw.mail.tests.QueuedMailTestMailBackend"):
        mailer.engine.send_all()

    return mail.queued_outbox


class EmailTransactionAssertionError(AssertionError):
    pass


class EmailSubjectAssertionError(AssertionError):
    pass


class CheckSubjectMixin:
    def check_messages(self, messages):
        # Subject check
        for m in messages:
            if not m.subject.startswith("[CCIW]"):
                if not _is_forwarded_message(m):
                    raise EmailSubjectAssertionError(f'Email with subject "{m.subject}" should start with [CCIW]')


class TestMailBackend(CheckSubjectMixin, LocMemEmailBackend):
    __test__ = False

    def send_messages(self, messages):
        # Transaction check
        if len(_NON_QUEUED_EMAIL_SENDING_DISALLOWED) > 0:
            raise EmailTransactionAssertionError(
                "Normal email should not be sent within transactions, use queued_mail instead"
            )
        self.check_messages(messages)

        return super().send_messages(messages)


class QueuedMailTestMailBackend(CheckSubjectMixin, BaseEmailBackend):
    # Same as Django's locmem EmailBackend, but uses 'queued_outbox' instead of 'outbox',
    # and uses CheckSubjectMixin
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(mail, "queued_outbox"):
            mail.queued_outbox = []

    def send_messages(self, messages):
        self.check_messages(messages)
        msg_count = 0
        for message in messages:  # .message() triggers header validation
            message.message()
            mail.queued_outbox.append(message)
            msg_count += 1
        return msg_count


class TestAtomicChecksMixin(AtomicChecksMixin, TestBase):
    # A test for our tests! Checking that TestMailBackend/Atomic monkey patching actually works
    def test_TestMailBackend_disallows_mail_within_atomic_blocks(self):
        with self.assertRaises(EmailTransactionAssertionError):
            with atomic():
                mail.send_mail("[CCIW] subject", "hello", "x@cciw.co.uk", ["x@example.com"])

    def test_TestMailBackend_allows_queued_mail_within_atomic_blocks(self):
        with atomic():
            queued_mail.send_mail("[CCIW] subject", "hello", "x@cciw.co.uk", ["x@example.com"])

    def test_TestMailBackend_enforces_subject(self):
        with self.assertRaises(EmailSubjectAssertionError):
            mail.send_mail("bad subject", "hello", "x@cciw.co.uk", ["x@example.com"])


def _is_forwarded_message(raw_message):
    message = email.message_from_bytes(raw_message.message().as_bytes(), policy=policy.SMTP)
    return "<noreply@cciw.co.uk>" in message["From"]


def make_message(
    *,
    from_email="Sam <a.person@example.com>",
    to_email="someone@cciw.co.uk",
    other_to_emails=None,
    subject="Test",
    additional_headers=None,
):
    if other_to_emails is None:
        # This exists to check mail is handled properly in cases like this:
        # To: someone@example.com, mylist@cciw.co.uk
        other_to_emails = [
            "Someone <someone@example.com>" '"Someone Else" <someone_else@example.com>',
        ]
    else:
        other_to_emails = []
    all_to_emails = other_to_emails + [to_email]
    if additional_headers is not None:
        extra_headers = "".join(encode_email_header(header) + "\n" for header in additional_headers)
    else:
        extra_headers = ""

    return emailify(
        f"""
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
Subject: {encode_email_header(subject)}
From: {encode_email_header(from_email)}
To: {encode_email_header(', '.join(all_to_emails))}
Date: Sun, 28 Feb 2016 22:32:03 -0000
Message-ID: <56CCDE2E.9030103@example.com>
{extra_headers}

Test message
    """
    )


def encode_email_header(header_value):
    if any(ord(c) > 127 for c in header_value):
        return email.header.Header(header_value, "utf-8").encode()
    return header_value


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
""".replace(
    b"\n", b"\r\n"
)


def make_plain_text_request(path, body, headers):
    mangled_headers = {"HTTP_" + name.replace("-", "_").upper(): value for name, value in headers.items()}
    return RequestFactory().generic(
        "POST", path, data=body, content_type="text/plain; charset=UTF-8", **mangled_headers
    )
