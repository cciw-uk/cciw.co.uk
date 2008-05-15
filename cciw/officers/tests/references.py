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
    fixtures = ['basic.yaml', 'officers_users.yaml']
    twill_quiet = False

    def _twill_login(self, creds):
        tc.go(mk_url("cciw.officers.views.index"))
        tc.fv(1, 'id_username', creds[0])
        tc.fv(1, 'id_password', creds[1])
        tc.submit()        

    def test_page_ok(self):
        self._twill_login(LEADER)
        tc.go(mk_url("cciw.officers.views.manage_references", year=2000, number=1))
        tc.code(200)
        tc.find('For camp 2000-1')
