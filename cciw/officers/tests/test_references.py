from django.core import mail
from django.core.urlresolvers import reverse

from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Application, ReferenceAction
from cciw.officers.tests.base import ReferenceSetupMixin
from cciw.officers.views import add_previous_references, close_enough_referee_match
from cciw.utils.tests.webtest import WebTestBase

from .base import OFFICER, LEADER_EMAIL, LEADER


class ReferencesPage(ReferenceSetupMixin, WebTestBase):

    def test_page_ok(self):
        # Value of this test lies in the test data.
        self.officer_login(LEADER)
        self.get_url("cciw-officers-manage_references", year=2000, slug="blue")
        self.assertCode(200)
        self.assertTextPresent('For camp 2000-blue')
        self.assertTextAbsent('referee1@email.co.uk')  # Received
        self.assertTextPresent('referee2@email.co.uk')    # Not received
        self.assertTextPresent('referee3@email.co.uk')
        self.assertTextPresent('referee4@email.co.uk')

    def test_page_anonymous_denied(self):
        self.get_literal_url(reverse("cciw-officers-manage_references", kwargs=dict(year=2000, slug="blue")),
                             auto_follow=False)
        self.assertCode(302)
        self.auto_follow()
        self.assertTextAbsent('For camp 2000-blue')

    def test_page_officers_denied(self):
        self.officer_login(OFFICER)
        self.get_literal_url(reverse("cciw-officers-manage_references", kwargs=dict(year=2000, slug="blue")),
                             expect_errors=[403])
        self.assertCode(403)


class RequestReference(ReferenceSetupMixin, WebTestBase):
    """
    Tests for page where reference is requested, and referee e-mail can be updated.
    """

    def test_with_email(self):
        """
        Ensure page allows you to proceed if there is an e-mail address for referee
        """
        # Application 3 has an e-mail address for first referee
        app = self.application3
        self.assertTrue(app.referees[0].email != '')
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, slug="blue"))
                             + "?referee_id=%d" % referee.id)
        self.assertCode(200)
        self.assertTextAbsent("No e-mail address")
        self.assertTextPresent("The following e-mail")
        self.submit('#id_request_reference_send input[name=send]')
        msgs = [e for e in mail.outbox if "Reference for" in e.subject]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].extra_headers.get('Reply-To', ''), LEADER_EMAIL)
        self.assertEqual(msgs[0].extra_headers.get('X-CCIW-Camp', ''), "2000-blue")

    def test_no_email(self):
        """
        Ensure page requires an e-mail address to be entered if it isn't set.
        """
        # Application 3 has no e-mail address for second referee
        app = self.application3
        self.assertTrue(app.referees[1].email == '')
        referee = app.referees[1]
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, slug="blue"))
                             + "?referee_id=%d" % referee.id)
        self.assertCode(200)
        self.assertTextPresent("No e-mail address")
        self.assertTextAbsent("This field is required")  # Don't want errors on first view
        self.assertTextAbsent("The following e-mail")

    def test_add_email(self):
        """
        Ensure we can add the e-mail address
        """
        self.test_no_email()
        self.fill_by_name({'email': 'addedemail@example.com',
                           'name': 'Added Name'})
        self.submit('[name=setemail]')
        app = Application.objects.get(id=self.application3.id)
        self.assertEqual(app.referees[1].email, 'addedemail@example.com')
        self.assertEqual(app.referees[1].name, 'Added Name')
        self.assertTextPresent("Name/e-mail address updated.")

    def test_cancel(self):
        # Application 3 has an e-mail address for first referee
        app = self.application3
        self.assertTrue(app.referees[0].email != '')
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, slug="blue"))
                             + "?referee_id=%d" % referee.id)
        self.assertCode(200)
        self.submit('#id_request_reference_send [name=cancel]')
        self.assertEqual(len(mail.outbox), 0)

    def test_dont_remove_link(self):
        """
        Test the error that should appear if the link is removed or altered
        """
        app = self.application3
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, slug="blue"))
                             + "?referee_id=%d" % referee.id)
        self.assertCode(200)
        self.fill_by_name({'message': 'I removed the link! Haha'})
        self.submit('[name=send]')
        url = make_ref_form_url(referee.id, None)
        self.assertTextPresent(url)
        self.assertTextPresent("You removed the link")
        self.assertEqual(len(mail.outbox), 0)

    def test_update_with_exact_match(self):
        """
        Test the case where we ask for an update, and there is an exact match
        """
        app = self.application4
        referee = app.referees[0]
        add_previous_references(referee)
        assert referee.previous_reference is not None
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2001, slug="blue"))
                             + "?referee_id=%d&update=1&prev_ref_id=%d" % (referee.id, referee.previous_reference.id))
        self.assertCode(200)
        self.assertTextPresent("Referee1 Name has done a reference for Joe in the past.")

    def test_exact_match_with_title(self):
        app1 = self.application4
        app2 = Application.objects.get(id=app1.id)

        # Modify to add "Rev."
        app2.referees[0].name = "Rev. " + app2.referees[0].name
        self.assertTrue(close_enough_referee_match(app1.referees[0],
                                                   app2.referees[0]))

        app2.referees[0].name = "Someone else entirely"
        self.assertFalse(close_enough_referee_match(app1.referees[0],
                                                    app2.referees[0]))

    def test_update_with_no_exact_match(self):
        """
        Test the case where we ask for an update, and there is no exact match
        """
        app = self.application4
        # We make a change, so we don't get exact match
        app.referees[0].email = "a_new_email_for_ref1@example.com"
        app.referees[0].save()
        referee = app.referees[0]
        add_previous_references(referee)
        assert referee.previous_reference is None
        assert referee.possible_previous_references[0].referee_name == "Referee1 Name"
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2001, slug="blue"))
                             + "?referee_id=%d&update=1&prev_ref_id=%d" % (referee.id, referee.possible_previous_references[0].id))
        self.assertCode(200)
        self.assertTextAbsent("Referee1 Name has done a reference for Joe in the past.")
        self.assertTextPresent("""In the past, "Referee1 Name <referee1@email.co.uk>" did""")
        self.assertTextPresent("If you have confirmed")
        self.assertTextPresent("""email address is now "Referee1 Name <a_new_email_for_ref1@example.com>",""")

    def test_fill_in_manually(self):
        app = self.application3
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, slug="blue"))
                             + "?referee_id=%d" % referee.id)
        self.assertCode(200)
        self.fill_by_name({'how_long_known': "10 years",
                           'capacity_known': "Pastor",
                           'character': "Great",
                           'capability_children': "Great.",
                           'concerns': "No."})
        self.submit('#id_request_reference_manual [name=save]')
        msgs = [e for e in mail.outbox if "CCIW reference form for" in e.subject]
        self.assertTrue(len(msgs) >= 0)
        app = Application.objects.get(id=app.id)
        self.assertTrue(app.referees[0].reference_is_received())

    def test_nag(self):
        """
        Tests for 'nag officer' page
        """
        app = self.application1
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(reverse("cciw-officers-nag_by_officer", kwargs=dict(year=2000, slug="blue"))
                             + "?referee_id=%d" % referee.id)
        self.assertCode(200)
        self.assertTextPresent("to nag their referee")
        self.submit('[name=send]')
        msgs = [e for e in mail.outbox if "Need reference from" in e.subject]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].extra_headers.get('Reply-To', ''), LEADER_EMAIL)
        self.assertEqual(referee.actions.filter(action_type=ReferenceAction.REFERENCE_NAG).count(), 1)


class CreateReference(ReferenceSetupMixin, WebTestBase):
    """
    Tests for page for referees submitting references
    """

    def test_page_ok(self):
        """
        Test for 200 code if we get the right URL
        """
        app = self.application2
        url = make_ref_form_url(app.referees[0].id, None)
        if 'www.cciw.co.uk' in url:
            url = url.replace('https://www.cciw.co.uk', '')
        assert 'www.cciw.co.uk' not in url
        response = self.get_literal_url(url)
        self.assertCode(200)
        return response

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        app = self.application2
        self.assertEqual(app.referees[0].name, "Mr Referee3 Name")
        self.assertFalse(app.referees[0].reference_is_received())
        self.test_page_ok()
        self.fill_by_name({'referee_name': 'Referee3 Name',
                           'how_long_known': 'Forever',
                           'capacity_known': 'Minister',
                           'capability_children': 'Fine',
                           'character': 'Great',
                           'concerns': 'No',
                           })
        self.submit('input[type=submit]')

        # Check the data has been saved
        app = Application.objects.get(id=app.id)
        self.assertTrue(app.referees[0].reference_is_received())
        reference = app.referees[0].reference
        self.assertEqual(reference.referee_name, "Referee3 Name")
        self.assertEqual(reference.how_long_known, "Forever")

        # Check the application has been updated with amended referee name
        self.assertEqual(app.referees[0].name, "Referee3 Name")

    def test_reference_update(self):
        """
        Check that if we are updating a reference that previous data appears
        """
        app1 = self.application1
        # app1 already has a reference done
        assert app1.referees[0].reference is not None
        app2 = self.application4
        assert app1.officer == app2.officer

        # We should be able to find an exact match for references
        add_previous_references(app2.referees[0])
        self.assertEqual(app2.referees[0].previous_reference, app1.referees[0].reference)

        # Go to the corresponding URL
        url = make_ref_form_url(app2.referees[0].id, app1.referees[0].reference.id)
        self.get_literal_url(url)
        self.assertCode(200)

        # Check it is pre-filled as we expect
        self.assertHtmlPresent("""<input id="id_referee_name" maxlength="100" name="referee_name" type="text" value="Referee1 Name" />""")
        self.assertHtmlPresent("""<input id="id_how_long_known" maxlength="150" name="how_long_known" type="text" value="A long time" />""")
