from client import CciwClient
from django.test import TestCase
from django.conf import settings
from cciw.cciwmain.models import Member
import cciw.cciwmain.views.members

import cciw.cciwmain.decorators

import os
import glob

TEST_MEMBER = 'test_member_1'
TEST_MEMBER_PASSWORD = 'password'

MEMBER_ADMIN_URL = '/memberadmin/preferences/'

def _get_file_size(path):
    return os.stat(path)[os.path.stat.ST_SIZE]

class MemberAdmin(TestCase):
    fixtures=['basic.yaml','test_members.yaml']
    def setUp(self):
        self.client = CciwClient()
        self.client.member_login(TEST_MEMBER, TEST_MEMBER_PASSWORD)
        self.member = Member.objects.get(user_name=TEST_MEMBER)

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
        f = open(iconpath)
        post_data = self._standard_post_data()
        post_data['icon'] = f
        
        response = self.client.post(MEMBER_ADMIN_URL, data=post_data)
        

    def test_upload_icon(self):
        new_icon = os.path.join(settings.TEST_DIR, TEST_MEMBER + ".png")
        # get length of file, used for heuristic
        fs = _get_file_size(new_icon)
        self.failIfEqual(fs, 0, "something has happened to %s" % new_icon) 

        # ensure the file isn't there already
        self._remove_member_icons()

        self._upload_icon(new_icon)

        # Ensure it got there
        uploaded = glob.glob(settings.MEDIA_ROOT + settings.MEMBER_ICON_PATH + self.member.user_name + ".*")[0]
        self.assertEqual(fs, _get_file_size(uploaded))

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

