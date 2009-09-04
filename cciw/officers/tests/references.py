import twill
from twill.shell import TwillCommandLoop
from twill import commands as tc

from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_django_url
from django.test import TestCase

from cciw.officers.models import Reference

OFFICER_USERNAME = 'mrofficer2'
OFFICER_PASSWORD = 'test_normaluser_password'
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)

LEADER_USERNAME = 'davestott'
LEADER_PASSWORD = 'test_normaluser_password'
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)

class ReferencesPage(TwillMixin, TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml', 'references.yaml']

    def test_page_ok(self):
        # Value of this test lies in the test data.
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.manage_references", year=2000, number=1))
        tc.code(200)
        tc.find('For camp 2000-1')
        tc.find('referee2@email.co.uk')
        tc.find('referee3@email.co.uk')
        tc.find('referee4@email.co.uk')

    def test_page_anonymous_denied(self):
        tc.go(make_django_url("cciw.officers.views.manage_references", year=2000, number=1))
        tc.code(200) # at a redirection page
        tc.notfind('For camp 2000-1')

    def test_page_officers_denied(self):
        self._twill_login(OFFICER)
        tc.go(make_django_url("cciw.officers.views.manage_references", year=2000, number=1))
        # Currently we get redirected to /officers/ page if insufficient
        # privileges.
        self.assertEqual(tc.get_browser().get_url().split('?')[0], make_django_url("cciw.officers.views.index"))
        tc.notfind('For camp 2000-1')

