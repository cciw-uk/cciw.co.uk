from __future__ import with_statement
import twill
from twill import commands as tc
from twill.shell import TwillCommandLoop

from BeautifulSoup import BeautifulSoup
from client import CciwClient
from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import mail

from cciw.cciwmain.models import Member, Message
import cciw.cciwmain.views.members
import cciw.cciwmain.decorators

from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_twill_url
from cciw.cciwmain.tests.mailhelpers import read_email_url
from cciw.cciwmain.tests.utils import init_query_caches

import datetime
import os
import glob
import urllib
import re

# created by fixture
TEST_MEMBER_USERNAME = 'test_member_1'
TEST_MEMBER_PASSWORD = 'password'
TEST_MEMBER_EMAIL = 'test@test.com'

TEST_POLL_CREATOR_USERNAME = 'test_poll_creator_1'
TEST_POLL_CREATOR_PASSWORD = 'password'

NEW_MEMBER_EMAIL='new_member@test.com'
NEW_MEMBER_USERNAME='new_member'
NEW_MEMBER_PASSWORD='mypassword'

MEMBER_ADMIN_URL = reverse("cciwmain.memberadmin.preferences")
MEMBER_SIGNUP = reverse("cciwmain.memberadmin.signup")

NEW_PASSWORD_URL = reverse("cciwmain.memberadmin.help_logging_in")


def _get_file_size(path):
    return os.stat(path)[os.path.stat.ST_SIZE]

def _remove_member_icons(user_name):
    for f in glob.glob("%s/%s/%s" % (settings.MEDIA_ROOT, settings.MEMBER_ICON_PATH, user_name + ".*")):
        os.unlink(f)


class MemberAdmin(TestCase):
    fixtures=['basic.json','test_members.json']
    def setUp(self):
        self.client = CciwClient()
        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        self.member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)

    def test_view_prefs(self):
        response = self.client.get(MEMBER_ADMIN_URL)
        self.assertEqual(response.status_code, 200)

        # Check we are on the right page
        self.assertEqual(response.templates[0].name,'cciw/members/preferences.html')

        # Check context has been populated
        member = response.context[0].get('member')
        self.assertTrue(member is not None)
        self.assertTrue(member == self.member)

    def _standard_post_data(self):
        return  {
            'real_name': self.member.real_name,
            'email': self.member.email,
            'show_email': self.member.show_email,
            'comments': self.member.comments,
            'message_option': self.member.message_option
        }

    def _upload_icon(self, iconpath):
        # Upload the file
        post_data = self._standard_post_data()
        f = open(iconpath)
        post_data['icon'] = f
        resp = self.client.post(MEMBER_ADMIN_URL, data=post_data, follow=True)
        f.close()
        return resp

    def test_upload_png_icon(self):
       self._test_upload_icon('png')

    def test_upload_gif_icon(self):
        self._test_upload_icon('gif')

    def test_upload_jpeg_icon(self):
        self._test_upload_icon('jpeg')

    def _test_upload_icon(self, ext):
        new_icon = os.path.join(settings.TEST_DIR, TEST_MEMBER_USERNAME + "." + ext)
        # get length of file, used for heuristic
        fs = _get_file_size(new_icon)
        self.assertNotEqual(fs, 0, "something has happened to %s" % new_icon)

        # ensure the file isn't there already
        _remove_member_icons(TEST_MEMBER_USERNAME)

        response = self._upload_icon(new_icon)
        self.assertEqual(response.status_code, 200)

        # Ensure it got there, converted to correct format
        dest_ext = settings.DEFAULT_MEMBER_ICON.split('.')[-1]
        globpath = "%s/%s/%s" % (settings.MEDIA_ROOT, settings.MEMBER_ICON_PATH, self.member.user_name + "." + dest_ext)
        files = glob.glob(globpath)
        self.assertEqual(1, len(files))
        self.assertNotEqual(0, _get_file_size(files[0]))

        return response

    def _assert_icon_upload_fails(self, filename):
        new_icon = os.path.join(settings.TEST_DIR, filename)

        # ensure the file isn't there already
        _remove_member_icons(TEST_MEMBER_USERNAME)

        resp = self._upload_icon(new_icon)

        # Ensure it didn't get there
        self.assertEqual(0, len(glob.glob("%s/%s/%s" % (settings.MEDIA_ROOT, settings.MEMBER_ICON_PATH, self.member.user_name + ".*"))))

        return resp

    def test_upload_bad_icon(self):
        resp = self._assert_icon_upload_fails("badicon.png")

    def test_upload_outsize_icon(self):
        resp = self._assert_icon_upload_fails("outsize_icon.png")
        # Ensure error message
        self.assertContains(resp, "The image was bigger than")

    def _read_email_change_email(self, email):
        return read_email_url(email, "https://.*/change-email/.*")

    def test_change_email(self):
        data = self._standard_post_data()
        data['email'] = "anewemailtoconfirm@email.com"
        resp = self.client.post(MEMBER_ADMIN_URL, data=data, follow=True)
        self.assertTrue("an e-mail has been sent" in resp.content)
        self.assertEqual(len(mail.outbox), 1)
        url, path, querydata = self._read_email_change_email(mail.outbox[0])
        resp2 = self.client.get(path, querydata)
        self.assertEqual(resp2.status_code, 200)

        m = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        self.assertEqual(m.email, data['email'])

    def _read_newpassword_email(self, email):
        return read_email_url(email, "https://.*/change-password/.*")

    def test_send_new_password(self):
        resp = self.client.post(NEW_PASSWORD_URL, {'email': TEST_MEMBER_EMAIL,
                                                   'newpassword': '1'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        url, path, querydata = self._read_newpassword_email(mail.outbox[0])
        newpassword_m = re.search(r"Your new password is:\s*(\S*)\s*", mail.outbox[0].body)
        self.assertTrue(newpassword_m is not None)
        newpassword = newpassword_m.groups()[0]

        self.client.get(path, querydata)
        m = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        self.assertTrue(m.check_password(newpassword))

    def tearDown(self):
        _remove_member_icons(TEST_MEMBER_USERNAME)


class MemberSignup(TwillMixin, TestCase):
    fixtures=['basic.json','test_members.json']

    def setUp(self):
        self.client = CciwClient()
        super(MemberSignup, self).setUp()

    def tearDown(self):
        super(MemberSignup, self).tearDown()
        _remove_member_icons(NEW_MEMBER_USERNAME)

    def test_existing_email(self):
        post_data = dict(submit_email='Submit', email=TEST_MEMBER_EMAIL)
        response = self.client.post(MEMBER_SIGNUP, data=post_data)
        self.assertEqual(response.status_code, 200)

        self.assertTrue("already used" in response.content,
                     "Signing up should not allow an existing email to be reused")
        self.assertEqual(len(mail.outbox), 0)

    def _test_signup_send_email_part1(self):
        post_data = dict(submit_email='Submit', email=NEW_MEMBER_EMAIL)
        response = self.client.post(MEMBER_SIGNUP, data=post_data)
        self.assertEqual(response.status_code, 200)

        self.assertTrue("an e-mail has been sent" in response.content,
                     "An message saying that an email has been sent should be seen")
        self.assertEqual(len(mail.outbox), 1, "An email should be sent")

    def _read_signup_email(self, email):
        return read_email_url(email, "https://.*/signup/.*")

    def _follow_email_url(self, path, querydata):
        response = self.client.get(path, querydata)
        self.assertEqual(response.status_code, 200)
        return response

    def test_signup_send_email(self):
        self._test_signup_send_email_part1()
        url, path, querydata = self._read_signup_email(mail.outbox[0])

    def test_signup_complete_correct(self):
        self._test_signup_send_email_part1()
        url, path, querydata = self._read_signup_email(mail.outbox[0])
        local_url = make_twill_url(url)
        tc.go(local_url)
        tc.notfind("Error")
        tc.fv('1', 'user_name', NEW_MEMBER_USERNAME)
        tc.fv('1', 'password1', NEW_MEMBER_PASSWORD)
        tc.fv('1', 'password2', NEW_MEMBER_PASSWORD)
        tc.submit()
        self._twill_assert_finished()

    def _twill_assert_finished(self):
        tc.find("Finished!")
        tc.find("Your account has been created")

    def test_signup_complete_bad_password(self):
        self._test_signup_send_email_part1()
        url, path, querydata = self._read_signup_email(mail.outbox[0])
        tc.go(make_twill_url(url))
        tc.notfind("Error")
        tc.fv('1', 'user_name', NEW_MEMBER_USERNAME)
        tc.fv('1', 'password1', NEW_MEMBER_PASSWORD)
        tc.fv('1', 'password2', NEW_MEMBER_PASSWORD + "x")
        tc.submit()
        tc.find("Error")

        # Correct it, without setting user_name
        tc.fv('1', 'password1', NEW_MEMBER_PASSWORD)
        tc.fv('1', 'password2', NEW_MEMBER_PASSWORD)

        # try again
        tc.submit()
        self._twill_assert_finished()

    def test_signup_complete_bad_username(self):
        self._test_signup_send_email_part1()
        url, path, querydata = self._read_signup_email(mail.outbox[0])
        tc.go(make_twill_url(url))
        tc.notfind("Error")
        tc.fv('1', 'user_name', TEST_MEMBER_USERNAME)
        tc.fv('1', 'password1', NEW_MEMBER_PASSWORD)
        tc.fv('1', 'password2', NEW_MEMBER_PASSWORD)
        tc.submit()
        tc.find("Error")

    def test_signup_incorrect_hash(self):
        self._test_signup_send_email_part1()
        url, path, querydata = self._read_signup_email(mail.outbox[0])
        querydata['h'] = querydata['h'] + "x"
        response = self._follow_email_url(path, querydata)
        self.assertTrue("Error" in response.content, "Error should be reported if the hash is incorrect")

    def test_signup_incorrect_email(self):
        self._test_signup_send_email_part1()
        url, path, querydata = self._read_signup_email(mail.outbox[0])
        querydata['email'] = querydata['email'] + "x"
        response = self._follow_email_url(path, querydata)
        self.assertTrue("Error" in response.content, "Error should be reported if the email is incorrect")


class MemberLists(TestCase):

    fixtures = ['basic.json','test_members.json']

    def setUp(self):
        super(MemberLists, self).setUp()
        self.factory = RequestFactory()
        init_query_caches()

    def test_index(self):
        resp = self.client.get(reverse('cciwmain.members.index'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp['Content-Type'].startswith('text/html'))
        self.assertContains(resp, TEST_MEMBER_USERNAME)

    def test_atom(self):
        # Just test for no error
        resp = self.client.get(reverse('cciwmain.members.index'), {'format':'atom'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/atom+xml')
        self.assertContains(resp, TEST_MEMBER_USERNAME)

    def test_query_count(self):
        for i in xrange(100):
            Member.objects.create(user_name="NewMember%d" % i,
                                  date_joined=datetime.datetime.now())

        from cciw.cciwmain.views.members import index

        request = self.factory.get(reverse('cciwmain.members.index'))
        with self.assertNumQueries(5):
            index(request).render()


        request = self.factory.get(reverse('cciwmain.members.index'), {'format':'atom'})
        with self.assertNumQueries(1):
            index(request)


class SendMessage(TestCase):

    fixtures = ['basic.json','test_members.json']

    def setUp(self):
        self.client = CciwClient()
        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        self.member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        self.other_member = Member.objects.get(user_name=TEST_POLL_CREATOR_USERNAME)
        self.member.messages_received.all().delete()
        self.other_member.messages_received.all().delete()

    def _send_msg_page(self):
        return reverse("cciwmain.members.send_message",
                       kwargs={'user_name': self.member.user_name})

    def _leave_msg_page(self):
        return reverse("cciwmain.members.send_message",
                       kwargs={'user_name': self.other_member.user_name})

    def test_send_page_get(self):
        """
        Tests that we can view the 'send message' page for sending to any user
        """
        resp = self.client.get(self._send_msg_page())
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Send a message")

    def test_leave_page_get(self):
        """
        Tests that we can view the 'leave message' page for leaving a message
        to a specific user.
        """
        resp = self.client.get(self._leave_msg_page())
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Leave a message")

    def test_send_page_post(self):
        """
        Tests that we can use the 'send message' page for sending to any user
        """
        resp = self.client.post(self._send_msg_page(),
                                {'to': self.other_member.user_name,
                                 'message': 'My message',
                                 'send': '1'},
                                follow=True)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Message was sent")
        self.assertEqual(self.other_member.messages_received.count(), 1)

    def test_leave_page_post(self):
        """
        Tests that we can use the 'leave message' page for leaving a message
        to a specific user.
        """
        resp = self.client.post(self._leave_msg_page(),
                                {'message': 'My message',
                                 'send': '1'},
                                follow=True)
        self.assertEqual(200, resp.status_code)

        self.assertContains(resp, "Message was sent")
        self.assertEqual(self.other_member.messages_received.count(), 1)

    def test_preview(self):
        """
        Tests that the preview functionality works
        """
        resp = self.client.post(self._leave_msg_page(),
                                {'message': '[b]My message',
                                 'preview': '1'},
                                follow=True)
        self.assertEqual(200, resp.status_code)
        # Check that the preview is there
        self.assertContains(resp, "<b>My message</b>")
        # Check that bbcode has been corrected
        self.assertContains(resp, "[b]My message[/b]")


class MessageLists(TestCase):

    fixtures = ['basic.json','test_members.json']

    def setUp(self):
        self.client = CciwClient()
        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        self.member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        self.member.messages_received.all().delete()

    def _get_inbox(self, page=None):
        if page is not None:
            qs = {'page': str(page)}
        else:
            qs = {}
        return self.client.get(reverse("cciwmain.members.inbox",
                                       kwargs={'user_name':TEST_MEMBER_USERNAME}),
                               qs)

    def _get_archived(self):
        return self.client.get(reverse("cciwmain.members.archived_messages",
                                       kwargs={'user_name':TEST_MEMBER_USERNAME}))

    def test_empty_inbox(self):
        # Sanity check:
        self.assertEqual(self.member.messages_received.filter(box=Message.MESSAGE_BOX_INBOX).count(), 0)
        resp = self._get_inbox()
        self.assertContains(resp, "No messages found", count=1)

    def _send_message(self, text):
        from_member = Member.objects.get(user_name=TEST_POLL_CREATOR_USERNAME)
        return Message.send_message(self.member, from_member, text)

    def test_inbox_with_message(self):
        msg = self._send_message("A quick message for you!")
        # Sanity check:
        self.assertEqual(self.member.messages_received.filter(box=Message.MESSAGE_BOX_INBOX).count(), 1)
        resp = self._get_inbox()
        self.assertContains(resp, msg.text, count=1)
        self.assertContains(resp, ">%s<" % msg.from_member.user_name, count=1)

    def _inbox_count(self):
        return self.member.messages_received.filter(box=Message.MESSAGE_BOX_INBOX).count()

    def _archived_count(self):
        return self.member.messages_received.filter(box=Message.MESSAGE_BOX_SAVED).count()

    def _msg_list_checkboxes(self, resp):
        b = BeautifulSoup(resp.content)
        checkboxes = [c for c in b.findAll(name='input', attrs={"type":"checkbox"})
                      if c.attrMap['name'].startswith('msg_')]
        return checkboxes

    def test_query_count(self):
        for i in xrange(settings.MEMBERS_PAGINATE_MESSAGES_BY):
            self._send_message("Message %s" % i)

        with self.assertNumQueries(8):
            resp = self._get_inbox()
            resp.render()

        for i in xrange(settings.MEMBERS_PAGINATE_MESSAGES_BY):
            self.assertContains(resp, "Message %s" % i)

    def test_archive_message_from_inbox(self):
        # Setup
        msg = self._send_message("A quick message")
        msg2 = self._send_message("Another message")
        inbox_count = self._inbox_count()
        archived_count = self._archived_count()

        # Get page
        resp = self._get_inbox()
        checkboxes = self._msg_list_checkboxes(resp)
        self.assertTrue(len(checkboxes) == inbox_count)

        # Archive
        resp2 = self.client.post(reverse("cciwmain.members.inbox",
                                         kwargs={'user_name': TEST_MEMBER_USERNAME}),
                                 {checkboxes[0].attrMap['name']: '1',
                                  'archive':'1'})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(self._inbox_count(), inbox_count - 1)
        self.assertEqual(self._archived_count(), archived_count + 1)

    def test_delete_message_from_inbox(self):
        # Setup
        msg = self._send_message("A quick message")
        inbox_count = self._inbox_count()
        # Get page
        resp = self._get_inbox()
        checkboxes = self._msg_list_checkboxes(resp)
        self.assertTrue(len(checkboxes) == inbox_count)

        # Delete
        resp2 = self.client.post(reverse("cciwmain.members.inbox",
                                         kwargs={'user_name': TEST_MEMBER_USERNAME}),
                                 {checkboxes[0].attrMap['name']: '1',
                                  'delete':'1'})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(self._inbox_count(), inbox_count - 1)

    def test_move_to_inbox_from_archive(self):
        # Setup
        msg = self._send_message("A quick message")
        msg2 = self._send_message("Another message")
        msg.box = Message.MESSAGE_BOX_SAVED
        msg2.box = Message.MESSAGE_BOX_SAVED
        msg.save()
        msg2.save()

        inbox_count = self._inbox_count()
        archived_count = self._archived_count()
        self.assertEqual(archived_count, 2)

        # Get page
        resp = self._get_archived()
        checkboxes = self._msg_list_checkboxes(resp)
        self.assertTrue(len(checkboxes) == archived_count)

        # Move to inbox
        resp2 = self.client.post(reverse("cciwmain.members.archived_messages",
                                         kwargs={'user_name': TEST_MEMBER_USERNAME}),
                                 {checkboxes[0].attrMap['name']: '1',
                                  'inbox':'1'})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(self._inbox_count(), inbox_count + 1)
        self.assertEqual(self._archived_count(), archived_count - 1)

    def test_redirect(self):
        """
        Ensure that we get a redirect if the user deletes the last message on a
        page to avoid a 404.
        """
        for i in range(0, settings.MEMBERS_PAGINATE_MESSAGES_BY + 1):
            self._send_message("Message number %s" % i)

        resp = self._get_inbox(page=2)
        checkboxes = self._msg_list_checkboxes(resp)
        # Sanity check
        self.assertTrue(len(checkboxes) == 1)

        # Delete
        resp2 = self.client.post(reverse("cciwmain.members.inbox",
                                         kwargs={'user_name': TEST_MEMBER_USERNAME})
                                 + "?page=2",
                                 {checkboxes[0].attrMap['name']: '1',
                                  'delete':'1'})
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue("page=1" in resp2['Location'])


class MemberPosts(TestCase):

    fixtures = ['basic.json','test_members.json', 'basic_topic.json']

    def test_index(self):
        resp = self.client.get(reverse('cciwmain.members.posts',
                                       kwargs={'user_name':TEST_MEMBER_USERNAME}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp['Content-Type'].startswith('text/html'))
        self.assertContains(resp, TEST_MEMBER_USERNAME)
        self.assertContains(resp, "unique message", count=1)

    def test_atom(self):
        # Just test for no error
        resp = self.client.get(reverse('cciwmain.members.posts',
                                       kwargs={'user_name':TEST_MEMBER_USERNAME}),
                               {'format':'atom'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/atom+xml')
        self.assertContains(resp, TEST_MEMBER_USERNAME)
        self.assertContains(resp, "unique message", count=1)
