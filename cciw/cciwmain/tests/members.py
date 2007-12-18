from client import CciwClient
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import mail

from cciw.cciwmain.models import Member
import cciw.cciwmain.views.members
import cciw.cciwmain.decorators

import os
import glob
import urllib
import urlparse
import re
import cgi

# created by fixture
TEST_MEMBER_USERNAME = 'test_member_1'
TEST_MEMBER_PASSWORD = 'password'
TEST_MEMBER_EMAIL = 'test@test.com' 

NEW_MEMBER_EMAIL='new_member@test.com'
NEW_MEMBER_USERNAME='new_member'

MEMBER_ADMIN_URL = reverse("cciwmain.memberadmin.preferences")
MEMBER_SIGNUP = reverse("cciwmain.memberadmin.signup")

def _get_file_size(path):
    return os.stat(path)[os.path.stat.ST_SIZE]

class MemberAdmin(TestCase):
    fixtures=['basic.yaml','test_members.yaml']
    def setUp(self):
        self.client = CciwClient()
        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        self.member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)

    def test_view_prefs(self):
        response = self.client.get(MEMBER_ADMIN_URL)
        self.failUnlessEqual(response.status_code, 200)

        # Check we are on the right page
        self.assertEqual(response.template[0].name,'cciw/members/preferences.html')

        # Check context has been populated
        member = response.context[0].get('member')
        self.assert_(member is not None)
        self.assert_(member == self.member)

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
        post_data['icon_file'] = open(iconpath)
        post_data['icon'] = ''
        return self.client.post(MEMBER_ADMIN_URL, data=post_data)

    def test_upload_icon(self):
        new_icon = os.path.join(settings.TEST_DIR, TEST_MEMBER_USERNAME + ".png")
        # get length of file, used for heuristic
        fs = _get_file_size(new_icon)
        self.failIfEqual(fs, 0, "something has happened to %s" % new_icon) 

        # ensure the file isn't there already
        self._remove_member_icons()

        response = self._upload_icon(new_icon)
        self.failUnlessEqual(response.status_code, 200)

        # Ensure it got there
        globpath = settings.MEDIA_ROOT + settings.MEMBER_ICON_PATH + self.member.user_name + ".*"
        files = glob.glob(globpath)
        self.assertEqual(1, len(files))
        self.assertEqual(fs, _get_file_size(files[0]))

    def _assert_icon_upload_fails(self, filename):
        new_icon = os.path.join(settings.TEST_DIR, filename)
        
        # ensure the file isn't there already
        self._remove_member_icons()

        self._upload_icon(new_icon)

        # Ensure it didn't get there
        self.assertEqual(0, len(glob.glob(settings.MEDIA_ROOT + settings.MEMBER_ICON_PATH + self.member.user_name + ".*")))

    def test_upload_bad_icon(self):
        self._assert_icon_upload_fails("badicon.png")

    def test_upload_outsize_icon(self):
        self._assert_icon_upload_fails("outsize_icon.png")

    def tearDown(self):
        self._remove_member_icons()
        pass

    def _remove_member_icons(self):
        for f in glob.glob(settings.MEDIA_ROOT + settings.MEMBER_ICON_PATH + self.member.user_name + ".*"):
            os.unlink(f)


def url_to_path_and_query(url):
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)    
    querydata_t = cgi.parse_qs(query)
    querydata = {}
    for key, val in querydata_t.items():
        querydata[key] = val[-1]
    return (path, querydata)

class MemberSignup(TestCase):
    fixtures=['basic.yaml','test_members.yaml']

    def setUp(self):
        self.client = CciwClient()

    def test_existing_email(self):
        post_data = dict(submit_email='Submit', email=TEST_MEMBER_EMAIL)
        response = self.client.post(MEMBER_SIGNUP, data=post_data)
        self.failUnlessEqual(response.status_code, 200)
   
        self.assert_("already used" in response.content,
                     "Signing up should not allow an existing email to be reused")
        self.assertEqual(len(mail.outbox), 0)


    def _test_signup_send_email_part1(self):
        post_data = dict(submit_email='Submit', email=NEW_MEMBER_EMAIL)
        response = self.client.post(MEMBER_SIGNUP, data=post_data)
        self.failUnlessEqual(response.status_code, 200)
   
        self.assert_("an e-mail has been sent" in response.content,
                     "An message saying that an email has been sent should be seen")
        self.assertEqual(len(mail.outbox), 1, "An email should be sent")
        

    def _read_signup_email(self, email):
        # read the email, and follow the link
        url = re.search("http://.*/signup/.*\w", email.body)
        self.assert_(url is not None, "No URL found in sent email")
        path, querydata = url_to_path_and_query(url.group())
        return path, querydata

    def _follow_email_url(self, path, querydata):
        response = self.client.get(path, querydata)
        self.failUnlessEqual(response.status_code, 200)
        return response
        
    def test_signup_send_email(self):
        self._test_signup_send_email_part1()
        path, querydata = self._read_signup_email(mail.outbox[0])

    def test_signup_complete_correct(self):
        self._test_signup_send_email_part1()
        path, querydata = self._read_signup_email(mail.outbox[0])
        response = self._follow_email_url(path, querydata)
        self.assert_("Error" not in response.content)
        # Fill out the form
        # TODO - test the rest of the process

    def test_signup_incorrect_hash(self):
        self._test_signup_send_email_part1()
        path, querydata = self._read_signup_email(mail.outbox[0])
        querydata['h'] = querydata['h'] + "x"
        response = self._follow_email_url(path, querydata)
        self.assert_("Error" in response.content, "Error should be reported if the hash is incorrect")

    def test_signup_incorrect_email(self):
        self._test_signup_send_email_part1()
        path, querydata = self._read_signup_email(mail.outbox[0])
        querydata['email'] = querydata['email'] + "x"
        response = self._follow_email_url(path, querydata)
        self.assert_("Error" in response.content, "Error should be reported if the email is incorrect")
