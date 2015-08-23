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
        self.webtest_officer_login(LEADER)
        response = self.get("cciw-officers-manage_references", year=2000, number=1)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'For camp 2000-1')
        self.assertNotContains(response, 'referee1@email.co.uk')  # Received
        self.assertContains(response, 'referee2@email.co.uk')    # Not received
        self.assertContains(response, 'referee3@email.co.uk')
        self.assertContains(response, 'referee4@email.co.uk')

    def test_page_anonymous_denied(self):
        response = self.get("cciw-officers-manage_references", year=2000, number=1)
        self.assertEqual(response.status_code, 302)
        self.assertNotContains(response.follow(), 'For camp 2000-1')

    def test_page_officers_denied(self):
        self.webtest_officer_login(OFFICER)
        response = self.app.get(reverse("cciw-officers-manage_references", kwargs=dict(year=2000, number=1)),
                                expect_errors=[403])
        self.assertEqual(response.status_code, 403)


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
        refinfo = app.references[0]
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, number=1))
                                + "?ref_id=%d" % refinfo.id)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No e-mail address")
        self.assertContains(response, "The following e-mail")
        response = response.forms['id_request_reference_send'].submit("send")
        msgs = [e for e in mail.outbox if "Reference for" in e.subject]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].extra_headers.get('Reply-To', ''), LEADER_EMAIL)

    def test_no_email(self):
        """
        Ensure page requires an e-mail address to be entered if it isn't set.
        """
        # Application 3 has no e-mail address for second referee
        app = self.application3
        self.assertTrue(app.referees[1].email == '')
        refinfo = app.references[1]
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, number=1))
                                + "?ref_id=%d" % refinfo.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No e-mail address")
        self.assertNotContains(response, "This field is required")  # Don't want errors on first view
        self.assertNotContains(response, "The following e-mail")
        return response

    def test_add_email(self):
        """
        Ensure we can add the e-mail address
        """
        response = self.test_no_email()
        response = self.fill(response.forms['id_set_email_form'],
                             {'email': 'addedemail@example.com',
                              'name': 'Added Name'}).submit('setemail')
        app = Application.objects.get(id=self.application3.id)
        self.assertEqual(app.referees[1].email, 'addedemail@example.com')
        self.assertEqual(app.referees[1].name, 'Added Name')
        self.assertContains(response, "Name/e-mail address updated.")

    def test_cancel(self):
        # Application 3 has an e-mail address for first referee
        app = self.application3
        self.assertTrue(app.referees[0].email != '')
        refinfo = app.references[0]
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, number=1))
                                + "?ref_id=%d" % refinfo.id)
        self.assertEqual(response.status_code, 200)
        response = response.forms['id_request_reference_send'].submit("cancel")
        self.assertEqual(len(mail.outbox), 0)

    def test_dont_remove_link(self):
        """
        Test the error that should appear if the link is removed or altered
        """
        app = self.application3
        refinfo = app.references[0]
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, number=1))
                                + "?ref_id=%d" % refinfo.id)
        self.assertEqual(response.status_code, 200)
        response = self.fill(response.forms['id_request_reference_send'],
                             {'message': 'I removed the link! Haha'}).submit('send')
        url = make_ref_form_url(refinfo.id, None)
        self.assertContains(response, url)
        self.assertContains(response, "You removed the link")
        self.assertEqual(len(mail.outbox), 0)

    def test_update_with_exact_match(self):
        """
        Test the case where we ask for an update, and there is an exact match
        """
        app = self.application4
        refinfo = app.references[0]
        add_previous_references(refinfo)
        assert refinfo.previous_reference is not None
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2001, number=1))
                                + "?ref_id=%d&update=1&prev_ref_id=%d" % (refinfo.id, refinfo.previous_reference.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Referee1 Name has done a reference for Joe in the past.")

    def test_exact_match_with_title(self):
        app1 = self.application4
        app2 = Application.objects.get(id=app1.id)

        # Modify to add "Rev."
        app2.referee1_name = "Rev. " + app2.referee1_name
        self.assertTrue(close_enough_referee_match(app1.referees[0],
                                                   app2.referees[0]))

        app2.referee1_name = "Someone else entirely"
        self.assertFalse(close_enough_referee_match(app1.referees[0],
                                                    app2.referees[0]))

    def test_update_with_no_exact_match(self):
        """
        Test the case where we ask for an update, and there is no exact match
        """
        app = self.application4
        # We make a change, so we don't get exact match
        app.referees[0].email = "a_new_email_for_ref1@example.com"
        app.save()
        refinfo = app.references[0]
        add_previous_references(refinfo)
        assert refinfo.previous_reference is None
        assert refinfo.possible_previous_references[0].reference_form.referee_name == "Referee1 Name"
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2001, number=1))
                                + "?ref_id=%d&update=1&prev_ref_id=%d" % (refinfo.id, refinfo.possible_previous_references[0].id))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Referee1 Name has done a reference for Joe in the past.")
        self.assertContains(response, """In the past, "Referee1 Name &lt;referee1@email.co.uk&gt;" did""")
        self.assertContains(response, "If you have confirmed")
        self.assertContains(response, """email address is now "Referee1 Name &lt;a_new_email_for_ref1@example.com&gt;",""")

    def test_fill_in_manually(self):
        app = self.application3
        refinfo = app.references[0]
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2000, number=1))
                                + "?ref_id=%d" % refinfo.id)
        self.assertEqual(response.status_code, 200)
        form = response.forms['id_request_reference_manual']
        form.set('how_long_known', "10 years")
        form.set('capacity_known', "Pastor")
        form.set('character', "Great")
        form.set('capability_children', "Great.")
        form.set('concerns', "No.")
        response = form.submit("save")
        msgs = [e for e in mail.outbox if "CCIW reference form for" in e.subject]
        self.assertTrue(len(msgs) >= 0)
        refinfo = refinfo.__class__.objects.get(id=refinfo.id)
        self.assertTrue(refinfo.received)

    def test_nag(self):
        """
        Tests for 'nag officer' page
        """
        app = self.application1
        refinfo = app.references[0]
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-nag_by_officer", kwargs=dict(year=2000, number=1))
                                + "?ref_id=%d" % refinfo.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "to nag their referee")
        response = response.forms[0].submit('send')
        msgs = [e for e in mail.outbox if "Need reference from" in e.subject]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].extra_headers.get('Reply-To', ''), LEADER_EMAIL)
        self.assertEqual(refinfo.actions.filter(action_type=ReferenceAction.REFERENCE_NAG).count(), 1)


class CreateReference(ReferenceSetupMixin, WebTestBase):
    """
    Tests for page for referees submitting references
    """

    def test_page_ok(self):
        """
        Test for 200 code if we get the right URL
        """
        app = self.application2
        url = make_ref_form_url(app.references[0].id, None)
        if 'www.cciw.co.uk' in url:
            url = url.replace('https://www.cciw.co.uk', '')
        assert 'www.cciw.co.uk' not in url
        response = self.get(url)
        self.assertEqual(response.status_code, 200)
        return response

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        app = self.application2
        self.assertEqual(app.referees[0].name, "Mr Referee3 Name")
        self.assertTrue(app.references[0].reference_form is None)
        response = self.test_page_ok()
        response = self.fill(response.forms['id_create_reference'],
                             {'referee_name': 'Referee3 Name',
                              'how_long_known': 'Forever',
                              'capacity_known': 'Minister',
                              'capability_children': 'Fine',
                              'character': 'Great',
                              'concerns': 'No',
                              }).submit()

        # Check the data has been saved
        app = Application.objects.get(id=app.id)
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
        app1 = self.application1
        # app1 already has a reference done
        assert app1.references[0].reference_form is not None
        app2 = self.application4
        assert app1.officer == app2.officer

        # We should be able to find an exact match for references
        add_previous_references(app2.references[0])
        self.assertEqual(app2.references[0].previous_reference, app1.references[0])

        # Go to the corresponding URL
        url = make_ref_form_url(app2.references[0].id, app1.references[0].id)
        response = self.get(url)
        self.assertEqual(response.status_code, 200)

        # Check it is pre-filled as we expect
        self.assertContains(response, """<input id="id_referee_name" maxlength="100" name="referee_name" type="text" value="Referee1 Name" />""", html=True)
        self.assertContains(response, """<input id="id_how_long_known" maxlength="150" name="how_long_known" type="text" value="A long time" />""", html=True)
