import twill
from twill.shell import TwillCommandLoop
from twill import commands as tc

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Application
from cciw.officers.views import get_previous_references
from cciw.utils.tests.twillhelpers import TwillMixin, make_django_url, make_twill_url


OFFICER_USERNAME = 'mrofficer2'
OFFICER_PASSWORD = 'test_normaluser_password'
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)


LEADER_USERNAME = 'davestott'
LEADER_PASSWORD = 'test_normaluser_password'
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)


class ReferencesPage(TwillMixin, TestCase):

    fixtures = ['basic.json', 'officers_users.json', 'references.json']

    def test_page_ok(self):
        # Value of this test lies in the test data.
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.manage_references", year=2000, number=1))
        tc.code(200)
        tc.find('For camp 2000-1')
        tc.notfind('referee1@email.co.uk') # Received
        tc.find('referee2@email.co.uk')    # Not received
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


class RequestReference(TwillMixin, TestCase):
    """
    Tests for page where reference is requested, and referee e-mail can be updated.
    """

    fixtures = ReferencesPage.fixtures

    def test_with_email(self):
        """
        Ensure page allows you to proceed if there is an e-mail address for referee
        """
        # Application 3 has an e-mail address for first referee
        app = Application.objects.get(pk=3)
        self.assertTrue(app.referees[0].email != '')
        refinfo = app.references[0]
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.request_reference") + "?ref_id=%d" % refinfo.id)
        tc.code(200)
        tc.notfind("No e-mail address")
        tc.find("The following e-mail")
        tc.formvalue("2", "send", "send")
        tc.submit()
        self.assertEqual(len([e for e in mail.outbox if "Reference for" in e.subject]), 1)

    def test_no_email(self):
        """
        Ensure page requires an e-mail address to be entered if it isn't set.
        """
        # Application 3 has no e-mail address for second referee
        app = Application.objects.get(pk=3)
        self.assertTrue(app.referees[1].email == '')
        refinfo = app.references[1]
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.request_reference") + "?ref_id=%d" % refinfo.id)
        tc.code(200)
        tc.find("No e-mail address")
        tc.notfind("This field is required") # Don't want errors on first view
        tc.notfind("The following e-mail")

    def test_add_email(self):
        """
        Ensure we can add the e-mail address
        """
        self.test_no_email()
        tc.formvalue('1', 'email', 'addedemail@example.com')
        tc.submit()
        app = Application.objects.get(pk=3)
        self.assertTrue(app.referees[1].email == 'addedemail@example.com')
        tc.find("E-mail address updated.")

    def test_cancel(self):
        # Application 3 has an e-mail address for first referee
        app = Application.objects.get(pk=3)
        self.assertTrue(app.referees[0].email != '')
        refinfo = app.references[0]
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.request_reference") + "?ref_id=%d" % refinfo.id)
        tc.code(200)
        tc.formvalue("2", "cancel", "cancel")
        tc.submit()
        self.assertEqual(len(mail.outbox), 0)

    def test_dont_remove_link(self):
        """
        Test the error that should appear if the link is removed or altered
        """
        app = Application.objects.get(pk=3)
        refinfo = app.references[0]
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.request_reference") + "?ref_id=%d" % refinfo.id)
        tc.code(200)
        tc.formvalue('2', 'message', 'I removed the link! Haha')
        tc.submit()
        url = make_ref_form_url(refinfo.id, None)
        tc.find(url)
        tc.find("You removed the link")
        self.assertEqual(len(mail.outbox), 0)


class CreateReference(TwillMixin, TestCase):
    """
    Tests for page for referees submitting references
    """

    fixtures = ReferencesPage.fixtures

    #twill_quiet = False
    def test_page_ok(self):
        """
        Test for 200 code if we get the right URL
        """
        app = Application.objects.get(pk=2)
        url = make_ref_form_url(app.references[0].id, None)
        tc.go(make_twill_url(url))
        tc.code(200)

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        app = Application.objects.get(pk=2)
        self.assertEqual(app.referees[0].name, "Mr Referee3 Name")
        self.assertTrue(app.references[0].reference_form is None)
        self.test_page_ok()

        tc.formvalue('1', 'referee_name', 'Referee3 Name')
        tc.formvalue('1', 'how_long_known', 'Forever')
        tc.formvalue('1', 'capacity_known', 'Minister')
        tc.formvalue('1', 'capability_children', 'Fine')
        tc.formvalue('1', 'character', 'Great')
        tc.formvalue('1', 'concerns', 'No')
        tc.submit()

        # Check the data has been saved
        app = Application.objects.get(pk=2)
        ref_form = app.references[0].reference_form
        self.assertTrue(ref_form is not None)
        self.assertEqual(ref_form.referee_name, "Referee3 Name")
        self.assertEqual(ref_form.how_long_known, "Forever")

        # Check the application has been updated with amended referee name
        self.assertEqual(app.referees[0].name, "Referee3 Name")

    def test_reference_update(self):
        """
        Check that if we are updating a reference that previous data appears
        """
        # This is story style - start with submitting "last year's" reference.
        self.test_page_submit()

        app = Application.objects.get(pk=2)
        # Now officer makes a new application form based on original
        # (which was updated in test_page_submit)
        app2 = Application.objects.get(pk=2)
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
        tc.find('name="referee_name" value="Referee3 Name"')
        tc.find('name="how_long_known" value="Forever"')


class EditReferenceFormManually(TestCase):

    fixtures = ['basic.json', 'officers_users.json', 'references.json']

    def test_creates_referenceform(self):
        """
        Ensure that 'edit_reference_form_manually' creates a ReferenceForm if
        one doesn't exist initially
        """
        app = Application.objects.get(pk=2)
        ref = app.references[0]
        assert ref.reference_form is None
        self.client.login(username=LEADER_USERNAME, password=LEADER_PASSWORD)
        resp = self.client.get(reverse('cciw.officers.views.edit_reference_form_manually',
                                       kwargs={'ref_id': ref.id}))

        # Expect a redirect to admin page
        self.assertEqual(302, resp.status_code)
        self.assertTrue("admin/officers/referenceform" in resp['Location'])

        # Object should be created now.
        self.assertTrue(ref.reference_form is not None)
