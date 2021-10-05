from django.conf import settings
from django.core import mail
from django.urls import reverse

from cciw.cciwmain.common import CampId
from cciw.cciwmain.tests.base import factories as camps_factories
from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Application, ReferenceAction
from cciw.officers.tests.base import ReferenceSetupMixin, factories
from cciw.officers.views import add_previous_references, close_enough_referee_match
from cciw.utils.tests.webtest import WebTestBase

from .base import LEADER, LEADER_EMAIL


class ReferencesPage(WebTestBase):
    def test_page_ok(self):
        leader = factories.create_officer()
        officer = factories.create_officer()
        camp = camps_factories.create_camp(leaders=[leader], officers=[officer])
        application = factories.create_application(officer=officer, year=camp.year)
        factories.create_complete_reference(application.referees[0])  # Just one

        self.officer_login(leader)
        self.get_url("cciw-officers-manage_references", camp_id=camp.url_id)
        self.assertCode(200)
        self.assertTextPresent(f"For camp {camp.year}-{camp.name.lower()}")
        # Received:
        self.assertTextAbsent(application.referees[0].email)
        # Not received
        self.assertTextPresent(application.referees[1].email)
        self.assertTextPresent(application.referees[1].name)
        self.assertTextPresent("Ask for reference - choose from the options")

    def test_page_anonymous_denied(self):
        camp = camps_factories.create_camp()
        self.get_literal_url(
            reverse("cciw-officers-manage_references", kwargs=dict(camp_id=camp.url_id)), auto_follow=False
        )
        self.assertCode(302)
        self.auto_follow()
        self.assertTextAbsent("For camp {camp.year}")

    def test_page_officers_denied(self):
        camp = camps_factories.create_camp()
        self.officer_login()
        self.get_literal_url(
            reverse("cciw-officers-manage_references", kwargs=dict(camp_id=camp.url_id)), expect_errors=[403]
        )
        self.assertCode(403)


class RequestReference(ReferenceSetupMixin, WebTestBase):
    """
    Tests for page where reference is requested, and referee email can be updated.
    """

    def test_with_email(self):
        """
        Ensure page allows you to proceed if there is an email address for referee
        """
        # Application 3 has an email address for first referee
        app = self.application3
        assert app.referees[0].email != ""
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2000, "blue")))
            + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.assertTextAbsent("No email address")
        self.assertTextPresent("The following email")
        self.submit("#id_request_reference_send input[name=send]")
        msgs = [e for e in mail.outbox if "Reference for" in e.subject]
        assert len(msgs) == 1
        assert msgs[0].extra_headers.get("Reply-To", "") == LEADER_EMAIL
        assert msgs[0].extra_headers.get("X-CCIW-Camp", "") == "2000-blue"

    def test_no_email(self):
        """
        Ensure page requires an email address to be entered if it isn't set.
        """
        # Application 3 has no email address for second referee
        app = self.application3
        assert app.referees[1].email == ""
        referee = app.referees[1]
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2000, "blue")))
            + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.assertTextPresent("No email address")
        self.assertTextAbsent("This field is required")  # Don't want errors on first view
        self.assertTextAbsent("The following email")

    def test_add_email(self):
        """
        Ensure we can add the email address
        """
        self.test_no_email()
        self.fill_by_name({"email": "addedemail@example.com", "name": "Added Name"})
        self.submit("[name=setemail]")
        app = Application.objects.get(id=self.application3.id)
        assert app.referees[1].email == "addedemail@example.com"
        assert app.referees[1].name == "Added Name"
        self.assertTextPresent("Name/email address updated.")

    def test_cancel(self):
        # Application 3 has an email address for first referee
        app = self.application3
        assert app.referees[0].email != ""
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2000, "blue")))
            + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.submit("#id_request_reference_send [name=cancel]")
        assert len(mail.outbox) == 0

    def test_dont_remove_link(self):
        """
        Test the error that should appear if the link is removed or altered
        """
        app = self.application3
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2000, "blue")))
            + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.fill_by_name({"message": "I removed the link! Haha"})
        self.submit("[name=send]")
        url = make_ref_form_url(referee.id, None)
        self.assertTextPresent(url)
        self.assertTextPresent("You removed the link")
        assert len(mail.outbox) == 0

    def test_update_with_exact_match(self):
        """
        Test the case where we ask for an update, and there is an exact match
        """
        app = self.application4
        referee = app.referees[0]
        add_previous_references(referee)
        assert referee.previous_reference is not None
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2001, "blue")))
            + "?referee_id=%d&update=1&prev_ref_id=%d" % (referee.id, referee.previous_reference.id)
        )
        self.assertCode(200)
        self.assertTextPresent("Referee1 Name has done a reference for Joe in the past.")

    def test_exact_match_with_title(self):
        app1 = self.application4
        app2 = Application.objects.get(id=app1.id)

        # Modify to add "Rev."
        app2.referees[0].name = "Rev. " + app2.referees[0].name
        assert close_enough_referee_match(app1.referees[0], app2.referees[0])

        app2.referees[0].name = "Someone else entirely"
        assert not close_enough_referee_match(app1.referees[0], app2.referees[0])

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
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2001, "blue")))
            + "?referee_id=%d&update=1&prev_ref_id=%d" % (referee.id, referee.possible_previous_references[0].id)
        )
        self.assertCode(200)
        self.assertTextAbsent("Referee1 Name has done a reference for Joe in the past.")
        self.assertHtmlPresent(
            """<p>In the past,"""
            """<b>"Referee1 Name &lt;referee1@email.co.uk&gt;"</b>"""
            """did a reference for Joe. If you have confirmed that this person's name/email address is now"""
            """<b>"Referee1 Name &lt;a_new_email_for_ref1@example.com&gt;",</b>"""
            """you can ask them to update their reference.</p>"""
        )

    def test_fill_in_manually(self):
        app = self.application3
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=CampId(2000, "blue")))
            + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.fill_by_name(
            {
                "how_long_known": "10 years",
                "capacity_known": "Pastor",
                "character": "Great",
                "capability_children": "Great.",
                "concerns": "No.",
            }
        )
        self.submit("#id_request_reference_manual [name=save]")
        msgs = [e for e in mail.outbox if "Reference form for" in e.subject]
        assert len(msgs) >= 0
        app = Application.objects.get(id=app.id)
        assert app.referees[0].reference_is_received()

    def test_nag(self):
        """
        Tests for 'nag officer' page
        """
        app = self.application1
        referee = app.referees[0]
        self.officer_login(LEADER)
        self.get_literal_url(
            reverse("cciw-officers-nag_by_officer", kwargs=dict(camp_id=CampId(2000, "blue")))
            + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.assertTextPresent("to nag their referee")
        self.submit("[name=send]")
        msgs = [e for e in mail.outbox if "Need reference from" in e.subject]
        assert len(msgs) == 1
        assert msgs[0].extra_headers.get("Reply-To", "") == LEADER_EMAIL
        assert referee.actions.filter(action_type=ReferenceAction.ActionType.NAG).count() == 1


def make_local_url(url):
    url = url.replace("https://" + settings.PRODUCTION_DOMAIN, "")
    assert settings.PRODUCTION_DOMAIN not in url
    return url


class CreateReference(ReferenceSetupMixin, WebTestBase):
    """
    Tests for page for referees submitting references
    """

    def test_page_ok(self):
        """
        Test for 200 code if we get the right URL
        """
        app = self.application2
        url = make_local_url(make_ref_form_url(app.referees[0].id, None))
        response = self.get_literal_url(url)
        self.assertCode(200)
        # Safeguarding coordinator details should be present:
        self.assertTextPresent("Safe Guarder")
        self.assertTextPresent("01234 567890")
        return response

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        app = self.application2
        assert app.referees[0].name == "Mr Referee3 Name"
        assert not app.referees[0].reference_is_received()
        self.test_page_ok()
        self.fill_by_name(
            {
                "referee_name": "Referee3 Name",
                "how_long_known": "Forever",
                "capacity_known": "Minister",
                "capability_children": "Fine",
                "character": "Great",
                "concerns": "No",
            }
        )
        self.submit("input[type=submit]")

        # Check the data has been saved
        app = Application.objects.get(id=app.id)
        assert app.referees[0].reference_is_received()
        reference = app.referees[0].reference
        assert reference.referee_name == "Referee3 Name"
        assert reference.how_long_known == "Forever"

        # Check the application has been updated with amended referee name
        assert app.referees[0].name == "Referee3 Name"

        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "The following reference form has been submitted" in m.body
        assert "https://www.cciw.co.uk/officers/leaders/reference/" in m.body

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
        assert app2.referees[0].previous_reference == app1.referees[0].reference

        # Go to the corresponding URL
        url = make_local_url(make_ref_form_url(app2.referees[0].id, app1.referees[0].reference.id))
        self.get_literal_url(url)
        self.assertCode(200)

        # Check it is pre-filled as we expect
        self.assertHtmlPresent(
            """<input id="id_referee_name" maxlength="100" name="referee_name" type="text" value="Referee1 Name" required />"""
        )
        self.assertHtmlPresent(
            """<input id="id_how_long_known" maxlength="150" name="how_long_known" type="text" value="A long time" required />"""
        )
