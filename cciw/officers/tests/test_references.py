from datetime import date

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from time_machine import travel

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests import factories as camps_factories
from cciw.cciwmain.tests.base import SiteSetupMixin
from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Referee, ReferenceAction, close_enough_referee_match, get_previous_references
from cciw.officers.tests import factories
from cciw.officers.tests.base import RolesSetupMixin
from cciw.utils.tests.factories import Auto
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase


def create_camp_with_leader_and_officer(year=Auto, future=Auto, officer_role: str = Auto):
    """
    Creates a camp with a leader and officer for testing reference requests
    """
    camp = camps_factories.create_camp(
        leader=(leader := factories.create_officer()),
        year=year,
        future=future,
    )
    officer = factories.create_officer()
    factories.add_officers_to_camp(camp, [officer], role=officer_role)
    return camp, leader, officer


class ManageReferencesPageWT(WebTestBase):
    # Basic tests that can be done with WebTest
    def test_page_ok(self):
        camp, leader, officer = create_camp_with_leader_and_officer()
        application = factories.create_application(officer=officer, year=camp.year)
        factories.create_complete_reference(application.referees[0])  # Just one

        self.officer_login(leader)
        self.get_url("cciw-officers-manage_references", camp_id=camp.url_id)
        self.assertCode(200)
        self.assertTextPresent(camp.nice_name)
        # Received:
        self.assertTextAbsent(application.referees[0].email)
        # Not received
        self.assertTextPresent(application.referees[1].email)
        self.assertTextPresent(application.referees[1].name)

    def test_page_anonymous_denied(self):
        camp = camps_factories.create_camp()
        self.get_literal_url(
            reverse("cciw-officers-manage_references", kwargs=dict(camp_id=camp.url_id)), auto_follow=False
        )
        self.assertCode(302)
        self.auto_follow()
        self.assertTextAbsent("For camp {camp.year}")

    def test_page_officers_denied(self):
        camp, leader, officer = create_camp_with_leader_and_officer()
        self.officer_login(officer)
        self.get_literal_url(
            reverse("cciw-officers-manage_references", kwargs=dict(camp_id=camp.url_id)), expect_errors=[403]
        )
        self.assertCode(403)


class ManageReferencesPageSL(RolesSetupMixin, SeleniumBase):
    """
    Tests for managing references
    """

    def wait_until_dialog_closed(self):
        self.wait_until(lambda _: not self.is_element_displayed("dialog"))

    def start_manage_reference(self, referee_email: str = Auto) -> tuple[Camp, User, User, Referee]:
        camp, leader, officer = create_camp_with_leader_and_officer(future=True)
        app = factories.create_application(officer=officer, year=camp.year, referee1_email=referee_email)
        referee = app.referees[0]
        return camp, leader, officer, referee

    def start_manage_reference_page(self, referee_email: str = Auto) -> tuple[Camp, User, User, Referee]:
        camp, leader, officer, referee = self.start_manage_reference(referee_email=referee_email)
        self.officer_login(leader)
        self.get_url("cciw-officers-manage_references", camp_id=camp.url_id)
        return camp, leader, officer, referee

    def start_request_reference(self, referee_email: str = Auto) -> tuple[Camp, User, User, Referee]:
        camp, leader, officer, referee = self.start_manage_reference_page(referee_email=referee_email)
        self.click(f"#id-manage-reference-{referee.id} [name=request-reference]")
        self.wait_until_loaded(css_selector="#id_message")
        return camp, leader, officer, referee

    def test_with_email(self):
        """
        Ensure page allows you to proceed if there is an email address for referee
        """
        camp, leader, _, referee = self.start_request_reference()
        self.assertTextPresent("The following email")
        self.click("dialog input[name=send]")
        self.wait_until_dialog_closed()
        msgs = [e for e in mail.outbox if "Reference for" in e.subject]
        assert len(msgs) == 1
        assert msgs[0].to == [referee.email]
        assert msgs[0].extra_headers.get("Reply-To", "") == leader.email
        assert msgs[0].extra_headers.get("X-CCIW-Camp", "") == str(camp.url_id)

    def test_no_email(self):
        """
        Ensure page requires an email address to be entered if it isn't set.
        """
        camp, leader, officer, referee = self.start_request_reference(referee_email="")
        self.assertTextAbsent("This field is required")  # Don't want errors on first view

        # Should refuse to send if we press send
        self.click("[name=send]")
        self.wait_for_ajax()
        self.assertTextPresent("No email address")
        assert len(mail.outbox) == 0

    def test_dont_remove_link(self):
        """
        Test the error that should appear if the link is removed or altered
        """
        camp, leader, officer, referee = self.start_request_reference()
        self.fill_by_name({"message": "I removed the link! Haha"})
        self.click("[name=send]")
        self.wait_for_ajax()
        url = make_ref_form_url(referee.id, None)
        self.assertTextPresent(url)
        self.assertTextPresent("You removed the link")
        assert len(mail.outbox) == 0

    def test_cancel(self):
        camp, leader, officer, referee = self.start_manage_reference_page()
        self.click(f"#id-manage-reference-{referee.id} [name=request-reference]")
        self.click("dialog [name=cancel]")
        self.wait_until_dialog_closed()
        assert len(mail.outbox) == 0

    def test_set_referee_email(self):
        # Ensure we can add the email address
        camp, leader, officer, referee = self.start_manage_reference_page()
        self.click(f"#id-manage-reference-{referee.id} [name=correct-referee-details]")

        self.fill_by_name({"email": "addedemail@example.com", "name": "Added Name"})
        self.click("[name=save]")
        self.wait_until_dialog_closed()
        referee.refresh_from_db()
        assert referee.email == "addedemail@example.com"
        assert referee.name == "Added Name"
        assert referee.actions.filter(action_type=ReferenceAction.ActionType.DETAILS_CORRECTED).exists()

    def test_update_with_exact_match(self):
        """
        Test the case where we ask for an update, and there is an exact match
        """
        # First year setup
        with travel(date(2010, 1, 1)):
            camp1, leader, officer = create_camp_with_leader_and_officer(year=2010)
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
            prev_exact, prev_refs = get_previous_references(referee)
            assert prev_exact is not None
            self.officer_login(leader)
            self.get_url("cciw-officers-manage_references", camp_id=camp2.url_id)
            self.click(f"#id-manage-reference-{referee.id} [name=request-updated-reference]")
            self.wait_until_loaded("#id_message")
            self.assertTextPresent("Referee1 Name has done a reference for Joe in the past.")

    def test_update_with_no_exact_match(self):
        """
        Test the case where we ask for an update, and there is no exact match
        """
        # First year setup
        with travel(date(2010, 1, 1)):
            camp, leader, officer = create_camp_with_leader_and_officer(year=2010)
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
            prev_exact, prev_refs = get_previous_references(referee)
            assert prev_exact is None
            assert prev_refs[0].referee_name == "Referee1 Name"
            self.officer_login(leader)
            self.get_url("cciw-officers-manage_references", camp_id=camp_2.url_id)
            self.fill({f"#id-manage-reference-{referee.id} [name=prev_ref_id]": prev_refs[0].id})
            self.click(f"#id-manage-reference-{referee.id} [name=request-updated-reference-custom]")
            self.wait_for_ajax()
            self.assertTextAbsent(f"Referee1 Name has done a reference for {officer.first_name} in the past.")
            for frag in [
                "Referee1 Name <email_for_ref1@example.com>",
                f"did a reference for {officer.first_name}",
                "If you have confirmed that this person's name/email address is now",
                "Referee1 Name <a_new_email_for_ref1@example.com>",
                "you can ask them to update their reference",
            ]:
                self.assertTextPresent(frag)

    def test_fill_in_manually(self):
        camp, leader, officer, referee = self.start_manage_reference_page()
        self.click(f"#id-manage-reference-{referee.id} [name=fill-in-reference-manually]")
        self.fill_by_name(
            {
                "how_long_known": "10 years",
                "capacity_known": "Pastor",
                "character": "Great",
                "capability_children": "Great.",
                "concerns": "No.",
            },
            scroll=False,
        )
        self.click("#id_request_reference_manual [name=save]", scroll=False)
        self.wait_for_ajax()
        msgs = [e for e in mail.outbox if "Reference form for" in e.subject]
        assert len(msgs) >= 0
        referee.refresh_from_db()
        assert referee.reference_is_received()

    def test_nag(self):
        """
        Tests for 'nag officer' page
        """
        camp, leader, officer, referee = self.start_manage_reference()
        referee.log_request_made(leader, timezone.now())
        self.officer_login(leader)
        self.get_url("cciw-officers-manage_references", camp_id=camp.url_id)

        self.click(f"#id-manage-reference-{referee.id} [name=nag-by-officer]")
        self.wait_until_loaded(css_selector="#id_message")
        self.assertTextPresent("to nag their referee")
        self.click("[name=send]")
        self.wait_until_dialog_closed()
        msgs = [e for e in mail.outbox if "Need reference from" in e.subject]
        assert len(msgs) == 1
        assert msgs[0].extra_headers.get("Reply-To", "") == leader.email
        assert referee.actions.filter(action_type=ReferenceAction.ActionType.NAG).count() == 1


def test_exact_match_with_title():
    assert close_enough_referee_match(
        Referee(name="Joe Bloggs", email="me@example.com"),
        Referee(name="Rev. Joe Bloggs", email="me@example.com"),
    )

    assert not close_enough_referee_match(
        Referee(name="Joe Bloggs", email="me@example.com"),
        Referee(name="Someone else entirely", email="me@example.com"),
    )


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
        officer = application.officer
        url = make_local_url(make_ref_form_url(application.referees[0].id, None))
        self.get_literal_url(url)
        self.assertCode(200)
        # Safeguarding coordinator details should be present:
        self.assertTextPresent(safeguarding_coordinator.full_name)
        self.assertTextPresent(safeguarding_coordinator.contact_phone_number)

        # No 'role' set in this case:
        self.assertTextPresent(f"{officer.full_name} has requested we collect a reference from you")

    def test_role_name_present(self):
        camp, leader, officer = create_camp_with_leader_and_officer(officer_role="Tent Officer")
        application = factories.create_application(officer=officer, year=camp.year, referee1_name="Mr Referee Name")
        url = make_local_url(make_ref_form_url(application.referees[0].id, None))
        self.get_literal_url(url)
        self.assertCode(200)

        self.assertTextPresent(f"{officer.full_name} will be on camp in the role of Tent Officer")
        self.assertTextPresent("has requested we collect a reference from you")

        # Add some more roles
        camp2 = camps_factories.create_camp(year=camp.year)
        factories.add_officers_to_camp(camp2, [officer], role="Tent Officer")
        camp3 = camps_factories.create_camp(year=camp.year)
        factories.add_officers_to_camp(camp3, [officer], role="Kitchen Helper")

        self.get_literal_url(url)
        self.assertTextPresent(f"{officer.full_name} will be on camp in the role of Kitchen Helper and Tent Officer")

    def test_page_submit(self):
        """
        Check that a reference can be created using the page,
        and that the name on the application form is updated.
        """
        camp, leader, officer = create_camp_with_leader_and_officer()
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
        prev_exact, prev_refs = get_previous_references(app2.referees[0])
        assert prev_exact == app1.referees[0].reference

        # Go to the corresponding URL
        url = make_local_url(make_ref_form_url(app2.referees[0].id, app1.referees[0].reference.id))
        self.get_literal_url(url)
        self.assertCode(200)

        # Check it is pre-filled as we expect
        assert self.get_element_attribute("#id_referee_name", "value") == "Referee1 Name"
        assert self.get_element_attribute("#id_how_long_known", "value") == "A long time"

        self.submit("input[type=submit]")
        app2.refresh_from_db()
        assert app2.referees[0].reference_is_received()
        reference = app2.referees[0].reference
        assert reference.referee_name == app1.referees[0].reference.referee_name
        assert reference.previous_reference == app1.referees[0].reference
