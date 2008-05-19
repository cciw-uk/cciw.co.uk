import twill
from twill.shell import TwillCommandLoop
from twill import commands as tc

from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_twill_url
from django.test import TestCase
from django.core.urlresolvers import reverse

from cciw.officers.models import Reference

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

    def test_change_data(self):
        self._twill_login(LEADER)
        tc.go(mk_url("cciw.officers.views.manage_references", year=2000, number=1))


        # Check the data is what we expect first, or the
        # test is bogus
        b = tc.get_browser()
        f = b.get_form(1)
        self.assertEqual(b.get_form_field(f, 'req_1_1').value, ['1'])
        self.assertEqual(b.get_form_field(f, 'req_2_1').value, ['1'])
        self.assertEqual(b.get_form_field(f, 'req_1_2').value, [])
        self.assertEqual(b.get_form_field(f, 'req_2_2').value, ['1'])
        self.assertEqual(b.get_form_field(f, 'req_1_3').value, [])
        self.assertEqual(b.get_form_field(f, 'req_2_3').value, [])

        self.assertEqual(b.get_form_field(f, 'rec_1_1').value, ['1'])
        self.assertEqual(b.get_form_field(f, 'rec_2_1').value, [])
        self.assertEqual(b.get_form_field(f, 'rec_1_2').value, [])
        self.assertEqual(b.get_form_field(f, 'rec_2_2').value, [])
        self.assertEqual(b.get_form_field(f, 'rec_1_3').value, [])
        self.assertEqual(b.get_form_field(f, 'rec_2_3').value, [])

        self.assertEqual(b.get_form_field(f, 'comments_1_1').value, '')
        self.assertEqual(b.get_form_field(f, 'comments_2_1').value, 'Left message on answer phone\r\n')
        self.assertEqual(b.get_form_field(f, 'comments_1_2').value, '')
        self.assertEqual(b.get_form_field(f, 'comments_2_2').value, '')
        self.assertEqual(b.get_form_field(f, 'comments_1_3').value, '')
        self.assertEqual(b.get_form_field(f, 'comments_2_3').value, '')

        tc.fv(1, 'req_1_1', '0')
        tc.fv(1, 'req_2_1', '0')
        tc.fv(1, 'req_1_2', '1')
        tc.fv(1, 'req_2_2', '0')
        tc.fv(1, 'req_1_3', '1')
        tc.fv(1, 'req_2_3', '1')

        tc.fv(1, 'rec_1_1', '0')
        tc.fv(1, 'rec_2_1', '1')
        tc.fv(1, 'rec_1_2', '1')
        tc.fv(1, 'rec_2_2', '1')
        tc.fv(1, 'rec_1_3', '1')
        tc.fv(1, 'rec_2_3', '1')

        tc.fv(1, 'comments_1_1', '1')
        tc.fv(1, 'comments_2_1', '')
        tc.fv(1, 'comments_1_2', '2')
        tc.fv(1, 'comments_2_2', '3')
        tc.fv(1, 'comments_1_3', '4')
        tc.fv(1, 'comments_2_3', '5')

        tc.submit()

        ref1_1 = Reference.objects.get(application__id=1, referee_number=1)
        ref2_1 = Reference.objects.get(application__id=1, referee_number=2)
        ref1_2 = Reference.objects.get(application__id=2, referee_number=1)
        ref2_2 = Reference.objects.get(application__id=2, referee_number=2)
        ref1_3 = Reference.objects.get(application__id=3, referee_number=1)
        ref2_3 = Reference.objects.get(application__id=3, referee_number=2)

        self.assertEqual(ref1_1.requested, False)
        self.assertEqual(ref2_1.requested, False)
        self.assertEqual(ref1_2.requested, True)
        self.assertEqual(ref2_2.requested, False)
        self.assertEqual(ref1_3.requested, True)
        self.assertEqual(ref2_3.requested, True)

        self.assertEqual(ref1_1.received, False)
        self.assertEqual(ref2_1.received, True)
        self.assertEqual(ref1_2.received, True)
        self.assertEqual(ref2_2.received, True)
        self.assertEqual(ref1_3.received, True)
        self.assertEqual(ref2_3.received, True)

        self.assertEqual(ref1_1.comments, '1')
        self.assertEqual(ref2_1.comments, '')
        self.assertEqual(ref1_2.comments, '2')
        self.assertEqual(ref2_2.comments, '3')
        self.assertEqual(ref1_3.comments, '4')
        self.assertEqual(ref2_3.comments, '5')

