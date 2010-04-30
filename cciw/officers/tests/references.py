import twill
from twill.shell import TwillCommandLoop
from twill import commands as tc

from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_django_url, make_twill_url
from django.test import TestCase

from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Application
from cciw.officers.views import get_previous_references

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


class CreateReference(TwillMixin, TestCase):

    fixtures = ['basic.yaml', 'officers_users.yaml', 'references.yaml']

    #twill_quiet = False
    def test_page_ok(self):
        """
        Test for 200 code if we get the right URL
        """
        app = Application.objects.get(pk=1)
        url = make_ref_form_url(app.references[0].id, None)
        tc.go(make_twill_url(url))
        tc.code(200)

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        app = Application.objects.get(pk=1)
        self.assertEqual(app.referees[0].name, "Mr Referee1 Name")
        self.assert_(app.references[0].reference_form is None)
        self.test_page_ok()

        tc.formvalue('1', 'referee_name', 'Referee1 Name')
        tc.formvalue('1', 'how_long_known', 'Forever')
        tc.formvalue('1', 'capacity_known', 'Minister')
        tc.formvalue('1', 'capability_children', 'Fine')
        tc.formvalue('1', 'character', 'Great')
        tc.formvalue('1', 'concerns', 'No')
        tc.submit()

        # Check the data has been saved
        app = Application.objects.get(pk=1)
        ref_form = app.references[0].reference_form
        self.assert_(ref_form is not None)
        self.assertEqual(ref_form.referee_name, "Referee1 Name")
        self.assertEqual(ref_form.how_long_known, "Forever")

        # Check the application has been updated with amended referee name
        self.assertEqual(app.referees[0].name, "Referee1 Name")

    def test_reference_update(self):
        """
        Check that if we are updating a reference that previous data appears
        """
        # This is story style - start with submitting "last year's" reference.
        self.test_page_submit()

        app = Application.objects.get(pk=1)
        # Now officer makes a new application form based on original
        # (which was updated in test_page_submit)
        app2 = Application.objects.get(pk=1)
        app2.id = None # force creation of new
        app2.camp_id = 2
        app2.save()

        # We should be able to find an exact match for references
        prev_refs, exact = get_previous_references(app2.references[0])
        self.assertEqual(exact, app.references[0])

        # Go to the corresponding URL
        url = make_ref_form_url(app2.references[0].id, app.references[0].id)
        tc.go(make_twill_url(url))
        tc.code(200)

        # Check it is pre-filled as we expect
        tc.find('name="referee_name" value="Referee1 Name"')
        tc.find('name="how_long_known" value="Forever"')
