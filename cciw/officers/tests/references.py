import twill
from twill.shell import TwillCommandLoop
from twill import commands as tc

from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_twill_url
from django.test import TestCase
from django.core.urlresolvers import reverse

OFFICER_USERNAME = 'mrofficer'
OFFICER_PASSWORD = 'test_normaluser_password'
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)

LEADER_USERNAME = 'mrleader'
LEADER_PASSWORD = 'test_normaluser_password'
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)

BASE = "http://www.cciw.co.uk"
def mk_url(view, *args, **kwargs):
    return make_twill_url(BASE + reverse(view, args=args, kwargs=kwargs))

class ReferencesPage(TwillMixin, TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml', 'references.yaml']

    def _twill_login(self, creds):
        tc.go(mk_url("cciw.officers.views.index"))
        tc.fv(1, 'id_username', creds[0])
        tc.fv(1, 'id_password', creds[1])
        tc.submit()        

    def test_page_ok(self):
        # Value of this test lies in the test data.
        self._twill_login(LEADER)
        tc.go(mk_url("cciw.officers.views.manage_references", year=2000, number=1))
        tc.code(200)
        tc.find('For camp 2000-1')

        tc.find('name="appids" value="1"')
        tc.find('name="appids" value="2"')
        tc.find('name="appids" value="3"')

        tc.find('referee1@email.co.uk')
        tc.find('referee2@email.co.uk')
        tc.find('referee3@email.co.uk')
        tc.find('referee4@email.co.uk')

    def test_page_anonymous_denied(self):
        tc.go(mk_url("cciw.officers.views.manage_references", year=2000, number=1))
        tc.code(200) # at a redirection page
        tc.notfind('For camp 2000-1')


    def test_page_officers_denied(self):
        self._twill_login(OFFICER)
        tc.go(mk_url("cciw.officers.views.manage_references", year=2000, number=1))
        # Currently we get redirected to /officers/ page if insufficient
        # privileges.
        self.assertEqual(tc.get_browser().get_url().split('?')[0], mk_url("cciw.officers.views.index"))
        tc.notfind('For camp 2000-1')
