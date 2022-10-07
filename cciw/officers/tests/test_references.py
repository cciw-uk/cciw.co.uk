from datetime import date

from django.conf import settings
from django.core import mail
from django.urls import reverse
from time_machine import travel

from cciw.cciwmain.tests import factories as camps_factories
from cciw.cciwmain.tests.base import SiteSetupMixin
from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Referee, ReferenceAction
from cciw.officers.tests import factories
from cciw.officers.tests.base import RolesSetupMixin
from cciw.officers.views import add_previous_references, close_enough_referee_match
from cciw.utils.tests.factories import Auto
from cciw.utils.tests.webtest import WebTestBase


def create_camp_leader_officer(year=Auto, future=Auto):
    """
    Creates a camp with a leader and officer for testing reference requests
    """
    camp = camps_factories.create_camp(
        leader=(leader := factories.create_officer()),
        officers=[(officer := factories.create_officer())],
        year=year,
        future=future,
    )
    return camp, leader, officer


class ReferencesPage(WebTestBase):
    def test_page_ok(self):
        camp, leader, officer = create_camp_leader_officer()
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
        camp, leader, officer = create_camp_leader_officer()
        self.officer_login(officer)
        self.get_literal_url(
            reverse("cciw-officers-manage_references", kwargs=dict(camp_id=camp.url_id)), expect_errors=[403]
        )
        self.assertCode(403)


class RequestReference(RolesSetupMixin, WebTestBase):
    """
    Tests for page where reference is requested, and referee email can be updated.
    """

    def test_with_email(self):
        """
        Ensure page allows you to proceed if there is an email address for referee
        """
        camp, leader, officer = create_camp_leader_officer(future=True)
        app = factories.create_application(officer=officer, referee1_email="an_email@example.com")
        referee = app.referees[0]
        self.officer_login(leader)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp.url_id)) + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.assertTextAbsent("No email address")
        self.assertTextPresent("The following email")
        self.submit("#id_request_reference_send input[name=send]")
        msgs = [e for e in mail.outbox if "Reference for" in e.subject]
        assert len(msgs) == 1
        assert msgs[0].extra_headers.get("Reply-To", "") == leader.email
        assert msgs[0].extra_headers.get("X-CCIW-Camp", "") == str(camp.url_id)

    def test_no_email(self):
        """
        Ensure page requires an email address to be entered if it isn't set.
        """
        camp, leader, officer = create_camp_leader_officer(future=True)
        app = factories.create_application(officer=officer, referee1_email="")
        referee = app.referees[0]
        self.officer_login(leader)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp.url_id)) + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.assertTextPresent("No email address")
        self.assertTextAbsent("This field is required")  # Don't want errors on first view
        self.assertTextAbsent("The following email")

        # Ensure we can add the email address
        self.fill_by_name({"email": "addedemail@example.com", "name": "Added Name"})
        self.submit("[name=setemail]")
        app.refresh_from_db()
        assert app.referees[0].email == "addedemail@example.com"
        assert app.referees[0].name == "Added Name"
        self.assertTextPresent("Name/email address updated.")

    def test_cancel(self):
        camp, leader, officer = create_camp_leader_officer(future=True)
        app = factories.create_application(officer=officer, referee1_email="an_email@example.com")
        referee = app.referees[0]
        self.officer_login(leader)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp.url_id)) + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.submit("#id_request_reference_send [name=cancel]")
        assert len(mail.outbox) == 0

    def test_dont_remove_link(self):
        """
        Test the error that should appear if the link is removed or altered
        """
        camp, leader, officer = create_camp_leader_officer(future=True)
        app = factories.create_application(officer=officer)
        referee = app.referees[0]
        self.officer_login(leader)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp.url_id)) + f"?referee_id={referee.id}"
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
        # First year setup
        with travel(date(2010, 1, 1)):
            camp1, leader, officer = create_camp_leader_officer(year=2010)
            app1 = factories.create_application(officer=officer)
            factories.create_complete_reference(app1.referees[0])
        # Second year setup
        with travel(date(2011, 1, 1)):
            camp2 = camps_factories.create_camp(year=2011, officers=[officer], leader=leader)
            app2 = factories.create_application(
                officer=officer,
                referee1_name=app1.referees[0].name,
                referee1_email=app1.referees[0].email,
            )

            referee = app2.referees[0]
            add_previous_references(referee)
            assert referee.previous_reference is not None
            self.officer_login(leader)
            self.get_literal_url(
                reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp2.url_id))
                + "?referee_id=%d&update=1&prev_ref_id=%d" % (referee.id, referee.previous_reference.id)
            )
            self.assertCode(200)
            self.assertTextPresent("Referee1 Name has done a reference for Joe in the past.")

    def test_exact_match_with_title(self):
        assert close_enough_referee_match(
            Referee(name="Joe Bloggs", email="me@example.com"),
            Referee(name="Rev. Joe Bloggs", email="me@example.com"),
        )

        assert not close_enough_referee_match(
            Referee(name="Joe Bloggs", email="me@example.com"),
            Referee(name="Someone else entirely", email="me@example.com"),
        )

    def test_update_with_no_exact_match(self):
        """
        Test the case where we ask for an update, and there is no exact match
        """
        # First year setup
        with travel(date(2010, 1, 1)):
            camp, leader, officer = create_camp_leader_officer(year=2010)
        with travel(date(2010, 2, 1)):
            app1 = factories.create_application(
                officer=officer,
                referee1_name="Referee1 Name",
                referee1_email="email_for_ref1@example.com",
            )
        with travel(date(2010, 3, 1)):
            factories.create_complete_reference(referee=app1.referees[0])

        # Second year setup
        with travel(date(2011, 1, 1)):
            camp_2 = camps_factories.create_camp(year=2011, officers=[officer], leader=leader)
        with travel(date(2011, 4, 1)):
            app2 = factories.create_application(
                officer=officer,
                referee1_name="Referee1 Name",
                # We make a change, so we don't get exact match
                referee1_email="a_new_email_for_ref1@example.com",
            )

        # Tests
        with travel(date(2011, 5, 1)):
            referee = app2.referees[0]
            add_previous_references(referee)
            assert referee.previous_reference is None
            assert referee.possible_previous_references[0].referee_name == "Referee1 Name"
            self.officer_login(leader)
            self.get_literal_url(
                reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp_2.url_id))
                + "?referee_id=%d&update=1&prev_ref_id=%d" % (referee.id, referee.possible_previous_references[0].id)
            )
            self.assertCode(200)
            self.assertTextAbsent(f"Referee1 Name has done a reference for {officer.first_name} in the past.")
            self.assertHtmlPresent(
                """<p>In the past,"""
                """<b>"Referee1 Name &lt;email_for_ref1@example.com&gt;"</b>"""
                f"""did a reference for {officer.first_name}. If you have confirmed that this person's name/email address is now"""
                """<b>"Referee1 Name &lt;a_new_email_for_ref1@example.com&gt;",</b>"""
                """you can ask them to update their reference.</p>"""
            )

    def test_fill_in_manually(self):
        camp, leader, officer = create_camp_leader_officer(future=True)
        app = factories.create_application(officer=officer)
        referee = app.referees[0]
        self.officer_login(leader)
        self.get_literal_url(
            reverse("cciw-officers-request_reference", kwargs=dict(camp_id=camp.url_id)) + f"?referee_id={referee.id}"
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
        app.refresh_from_db()
        assert app.referees[0].reference_is_received()

    def test_nag(self):
        """
        Tests for 'nag officer' page
        """
        camp, leader, officer = create_camp_leader_officer(future=True)
        app = factories.create_application(officer=officer)
        referee = app.referees[0]
        self.officer_login(leader)
        self.get_literal_url(
            reverse("cciw-officers-nag_by_officer", kwargs=dict(camp_id=camp.url_id)) + f"?referee_id={referee.id}"
        )
        self.assertCode(200)
        self.assertTextPresent("to nag their referee")
        self.submit("[name=send]")
        msgs = [e for e in mail.outbox if "Need reference from" in e.subject]
        assert len(msgs) == 1
        assert msgs[0].extra_headers.get("Reply-To", "") == leader.email
        assert referee.actions.filter(action_type=ReferenceAction.ActionType.NAG).count() == 1


def make_local_url(url):
    url = url.replace("https://" + settings.PRODUCTION_DOMAIN, "")
    assert settings.PRODUCTION_DOMAIN not in url
    return url


class CreateReference(SiteSetupMixin, RolesSetupMixin, WebTestBase):
    """
    Tests for page for referees submitting references
    """

    def test_page_ok(self):
        """
        Test for 200 code if we get the right URL
        """
        safeguarding_coordinator = factories.create_safeguarding_coordinator()
        application = factories.create_application()
        url = make_local_url(make_ref_form_url(application.referees[0].id, None))
        self.get_literal_url(url)
        self.assertCode(200)
        # Safeguarding coordinator details should be present:
        self.assertTextPresent(safeguarding_coordinator.full_name)
        self.assertTextPresent(safeguarding_coordinator.contact_phone_number)

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        camp, leader, officer = create_camp_leader_officer()
        application = factories.create_application(officer=officer, year=camp.year, referee1_name="Mr Referee Name")
        assert not application.referees[0].reference_is_received()
        url = make_local_url(make_ref_form_url(application.referees[0].id, None))
        self.get_literal_url(url)
        self.assertCode(200)
        self.fill_by_name(
            {
                "referee_name": "Referee Name",
                "how_long_known": "Forever",
                "capacity_known": "Minister",
                "capability_children": "Fine",
                "character": "Great",
                "concerns": "No",
                "given_in_confidence": True,
            }
        )
        self.submit("input[type=submit]")

        # Check the data has been saved
        application.refresh_from_db()
        assert application.referees[0].reference_is_received()
        reference = application.referees[0].reference
        assert reference.referee_name == "Referee Name"
        assert reference.how_long_known == "Forever"
        assert reference.given_in_confidence

        # Check the application has been updated with amended referee name
        assert application.referees[0].name == "Referee Name"

        assert len(mail.outbox) == 1
        m = mail.outbox[0]
        assert "The following reference form has been submitted" in m.body
        assert "https://www.cciw.co.uk/officers/leaders/reference/" in m.body

    def test_reference_update(self):
        """
        Check that if we are updating a reference that previous data appears
        """
        officer = factories.create_officer()
        app1 = factories.create_application(officer=officer, year=2000)
        factories.create_complete_reference(app1.referees[0])
        app2 = factories.create_application(officer=officer, year=2001)

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
