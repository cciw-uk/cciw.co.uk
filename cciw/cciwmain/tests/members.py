import twill
from twill import commands as tc
from twill.shell import TwillCommandLoop

from client import CciwClient
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import mail

from cciw.cciwmain.models import Member
import cciw.cciwmain.views.members
import cciw.cciwmain.decorators

from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_twill_url
from cciw.cciwmain.tests.mailhelpers import read_email_url

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
        resp = self.client.post(MEMBER_ADMIN_URL, data=post_data)
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

    def _assert_icon_upload_fails(self, filename):
        new_icon = os.path.join(settings.TEST_DIR, filename)

        # ensure the file isn't there already
        _remove_member_icons(TEST_MEMBER_USERNAME)

        self._upload_icon(new_icon)

        # Ensure it didn't get there
        self.assertEqual(0, len(glob.glob("%s/%s/%s" % (settings.MEDIA_ROOT, settings.MEMBER_ICON_PATH, self.member.user_name + ".*"))))

    def test_upload_bad_icon(self):
        self._assert_icon_upload_fails("badicon.png")

    def test_upload_outsize_icon(self):
        self._assert_icon_upload_fails("outsize_icon.png")

    def _read_email_change_email(self, email):
        return read_email_url(email, "https://.*/change-email/.*")

    def test_change_email(self):
        data = self._standard_post_data()
        data['email'] = "anewemailtoconfirm@email.com"
        resp = self.client.post(MEMBER_ADMIN_URL, data=data)
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
    fixtures=['basic.json','test_members.json']

    def test_index(self):
        resp = self.client.get(reverse('cciwmain.members.index'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TEST_MEMBER_USERNAME in resp.content)

    def test_atom(self):
        # Just test for no error
        resp = self.client.get(reverse('cciwmain.members.index'), {'format':'atom'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TEST_MEMBER_USERNAME in resp.content)

class MemberPosts(TestCase):

    fixtures = ['basic.json','test_members.json', 'basic_topic.json']

    def test_index(self):
        resp = self.client.get(reverse('cciwmain.members.posts',
                                       kwargs={'user_name':TEST_MEMBER_USERNAME}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TEST_MEMBER_USERNAME in resp.content)

    def test_atom(self):
        # Just test for no error
        resp = self.client.get(reverse('cciwmain.members.posts',
                                       kwargs={'user_name':TEST_MEMBER_USERNAME}),
                               {'format':'atom'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TEST_MEMBER_USERNAME in resp.content)
