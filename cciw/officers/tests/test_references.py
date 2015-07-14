from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django_dynamic_fixture import G

from cciw.cciwmain.models import Camp
from cciw.officers.email import make_ref_form_url
from cciw.officers.models import Application, ReferenceAction, ReferenceForm, Reference
from cciw.officers.tests.base import OfficersSetupMixin
from cciw.officers.views import add_previous_references
from cciw.utils.tests.webtest import WebTestBase

from .base import OFFICER, LEADER_USERNAME, LEADER_PASSWORD, LEADER_EMAIL, LEADER

User = get_user_model()

# Data: Applications 1 to 3 are in year 2000, for camps in summer 2000
# Application 4 is for 2001

class ReferencesDataMixin(OfficersSetupMixin):

    def setUp(self):
        super(ReferencesDataMixin, self).setUp()

        self.officer1 = self.officer_user
        self.officer2 = G(User,
                          username="petersmith",
                          first_name="Peter",
                          last_name="Smith",
                          is_active=True,
                          is_superuser=False,
                          is_staff=True,
                          last_login="2008-04-23T14:49:25Z",
                          password="sha1$1b3b9$a8a863f2f021582d972b6e50629c8f8588de7bba",
                          email="petersmith@somewhere.com",
                          date_joined="2008-03-21T16:48:46Z"
                          )

        self.officer3 = G(User,
                          username="fredjones",
                          first_name="Fred",
                          last_name="Jones",
                          is_active=True,
                          is_superuser=False,
                          is_staff=True,
                          last_login="2008-04-23T14:49:25Z",
                          email="fredjones@somewhere.com",
                          date_joined="2008-03-21T16:48:46Z"
                          )

        self.application1 = G(Application,
                              officer=self.officer1,
                              address2_address="123 abc",
                              address2_from="2003/08",
                              address2_to="2004/06",
                              address3_address="456 zxc",
                              address3_from="1996/11",
                              address3_to="2003/08",
                              address_country="UK",
                              address_county="Yorkshire",
                              address_email="hey@boo.com",
                              address_firstline="654 Stupid Way",
                              address_mobile="",
                              address_postcode="XY9 8WN",
                              address_since="2004/06",
                              address_tel="01048378569",
                              address_town="Bradford",
                              allegation_declaration=False,
                              birth_date="1911-02-07",
                              birth_place="Foobar",
                              christian_experience="Became a Christian at age 0.2 years",
                              concern_declaration=False,
                              concern_details="",
                              court_declaration=False,
                              court_details="",
                              crb_check_consent=True,
                              crime_declaration=False,
                              crime_details="",
                              date_submitted="2000-03-01",
                              employer1_from="2003/09",
                              employer1_job="Pilot",
                              employer1_leaving="",
                              employer1_name="Employer 1",
                              employer1_to="0000/00",
                              employer2_from="1988/10",
                              employer2_job="Manager",
                              employer2_leaving="Just because",
                              employer2_name="Employer 2",
                              employer2_to="2003/06",
                              finished=True,
                              full_maiden_name="",
                              full_name="Joe Winston Bloggs",
                              illness_details="",
                              referee1_address="Referee 1 Address\r\nLine 2",
                              referee1_email="referee1@email.co.uk",
                              referee1_mobile="",
                              referee1_name="Mr Referee1 Name",
                              referee1_tel="01222 666666",
                              referee2_address="1267a Somewhere Road\r\nThereyougo",
                              referee2_email="referee2@email.co.uk",
                              referee2_mobile="",
                              referee2_name="Mr Referee2 Name",
                              referee2_tel="01234 567890",
                              relevant_illness=False,
                              youth_experience="Lots",
                              youth_work_declined=False,
                              youth_work_declined_details="",
                              )
        self.application2 = G(Application,
                              officer=self.officer2,
                              address2_address="123 abc",
                              address2_from="2003/08",
                              address2_to="2004/06",
                              address3_address="456 zxc",
                              address3_from="1996/11",
                              address3_to="2003/08",
                              address_country="UK",
                              address_county="Yorkshire",
                              address_email="hey@boo.com",
                              address_firstline="654 Stupid Way",
                              address_mobile="",
                              address_postcode="XY9 8WN",
                              address_since="2004/06",
                              address_tel="01048378569",
                              address_town="Bradford",
                              allegation_declaration=False,
                              birth_date="1911-02-07",
                              birth_place="Foobar",
                              christian_experience="Became a Christian at age 0.2 years",
                              concern_declaration=False,
                              concern_details="",
                              court_declaration=False,
                              court_details="",
                              crb_check_consent=True,
                              crime_declaration=False,
                              crime_details="",
                              date_submitted="2000-03-01",
                              employer1_from="2003/09",
                              employer1_job="Pilot",
                              employer1_leaving="",
                              employer1_name="Employer 1",
                              employer1_to="0000/00",
                              employer2_from="1988/10",
                              employer2_job="Manager",
                              employer2_leaving="Just because",
                              employer2_name="Employer 2",
                              employer2_to="2003/06",
                              finished=True,
                              full_maiden_name="",
                              full_name="Peter Smith",
                              illness_details="",
                              referee1_address="Referee 3 Address\r\nLine 2",
                              referee1_email="referee3@email.co.uk",
                              referee1_mobile="",
                              referee1_name="Mr Referee3 Name",
                              referee1_tel="01222 666666",
                              referee2_address="Referee 4 adddress",
                              referee2_email="referee4@email.co.uk",
                              referee2_mobile="",
                              referee2_name="Mr Referee4 Name",
                              referee2_tel="01234 567890",
                              relevant_illness=False,
                              youth_experience="Lots",
                              youth_work_declined=False,
                              youth_work_declined_details="",
                          )

        self.application3 = G(Application,
                              officer=self.officer3,
                              address2_address="123 abc",
                              address2_from="2003/08",
                              address2_to="2004/06",
                              address3_address="456 zxc",
                              address3_from="1996/11",
                              address3_to="2003/08",
                              address_country="UK",
                              address_county="Yorkshire",
                              address_email="hey@boo.com",
                              address_firstline="654 Stupid Way",
                              address_mobile="",
                              address_postcode="XY9 8WN",
                              address_since="2004/06",
                              address_tel="01048378569",
                              address_town="Bradford",
                              allegation_declaration=False,
                              birth_date="1911-02-07",
                              birth_place="Foobar",
                              christian_experience="Became a Christian at age 0.2 years",
                              concern_declaration=False,
                              concern_details="",
                              court_declaration=False,
                              court_details="",
                              crb_check_consent=True,
                              crime_declaration=False,
                              crime_details="",
                              date_submitted="2000-03-01",
                              employer1_from="2003/09",
                              employer1_job="Pilot",
                              employer1_leaving="",
                              employer1_name="Employer 1",
                              employer1_to="0000/00",
                              employer2_from="1988/10",
                              employer2_job="Manager",
                              employer2_leaving="Just because",
                              employer2_name="Employer 2",
                              employer2_to="2003/06",
                              finished=True,
                              full_maiden_name="",
                              full_name="Fred Jones",
                              illness_details="",
                              referee1_address="Referee 5 Address\r\nLine 2",
                              referee1_email="referee5@email.co.uk",
                              referee1_mobile="",
                              referee1_name="Mr Refere5 Name",
                              referee1_tel="01222 666666",
                              referee2_address="Referee 6 adddress",
                              referee2_email="",
                              referee2_mobile="",
                              referee2_name="Mr Referee6 Name",
                              referee2_tel="01234 567890",
                              relevant_illness=False,
                              youth_experience="Lots",
                              youth_work_declined=False,
                              youth_work_declined_details="",
                              )

        self.application4 = Application.objects.get(id=self.application1.id)
        self.application4.id = None  # force save as new
        self.application4.date_submitted += timedelta(days=365)
        self.application4.save()

        self.reference1_1 = self.application1.reference_set.create(
            referee_number=1,
            received=True,
            requested=True
        )
        self.referenceform_1_1 = G(ReferenceForm,
                                   reference_info=self.reference1_1,
                                   referee_name="Mr Referee1 Name",
                                   how_long_known="A long time",
                                   capacity_known="Pastor",
                                   known_offences=False,
                                   capability_children="Wonderful",
                                   character="Almost sinless",
                                   concerns="Perhaps too good for camp",
                                   comments="",
                                   date_created="2000-02-20",
                                   )
        self.reference1_2 = self.application1.reference_set.create(
            referee_number=2,
            received=False,
            requested=True,
            comments="Left message on phone",
        )

        self.reference2_2 = self.application2.reference_set.create(
            referee_number=2,
            received=False,
            requested=True,
        )

        camp = Camp.objects.get(year=2000, number=1)

        camp.invitations.create(
            officer=self.officer1,
        )
        camp.invitations.create(
            officer=self.officer2,
        )
        camp.invitations.create(
            officer=self.officer3,
        )

class ReferencesPage(ReferencesDataMixin, WebTestBase):

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


class RequestReference(ReferencesDataMixin, WebTestBase):
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
        response = response.forms['id_request_reference'].submit("send")
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
        response = response.forms['id_request_reference'].submit("cancel")
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
        response = self.fill(response.forms['id_request_reference'],
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
        self.assertContains(response, "Mr Referee1 Name has done a reference for Joe in the past.")

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
        assert refinfo.possible_previous_references[0].reference_form.referee_name == "Mr Referee1 Name"
        self.webtest_officer_login(LEADER)
        response = self.app.get(reverse("cciw-officers-request_reference", kwargs=dict(year=2001, number=1))
                                + "?ref_id=%d&update=1&prev_ref_id=%d" % (refinfo.id, refinfo.possible_previous_references[0].id))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Mr Referee1 Name has done a reference for Joe in the past.")
        self.assertContains(response, """In the past, "Mr Referee1 Name &lt;referee1@email.co.uk&gt;" did""")
        self.assertContains(response, "If you have confirmed")
        self.assertContains(response, """email address is now "Mr Referee1 Name &lt;a_new_email_for_ref1@example.com&gt;",""")

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


class CreateReference(ReferencesDataMixin, WebTestBase):
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
        self.assertContains(response, """<input id="id_referee_name" maxlength="100" name="referee_name" type="text" value="Mr Referee1 Name" />""", html=True)
        self.assertContains(response, """<input id="id_how_long_known" maxlength="150" name="how_long_known" type="text" value="A long time" />""", html=True)


class EditReferenceFormManually(ReferencesDataMixin, TestCase):

    def test_creates_referenceform(self):
        """
        Ensure that 'edit_reference_form_manually' creates a ReferenceForm if
        one doesn't exist initially
        """
        app = self.application2
        ref = app.references[0]
        assert ref.reference_form is None
        self.client.login(username=LEADER_USERNAME, password=LEADER_PASSWORD)
        resp = self.client.get(reverse('cciw-officers-edit_reference_form_manually',
                                       kwargs={'ref_id': ref.id}))

        # Expect a redirect to admin page
        self.assertEqual(302, resp.status_code)
        self.assertTrue("admin/officers/referenceform" in resp['Location'])

        # Object should be created now.
        ref = ref.__class__.objects.get(id=ref.id)
        self.assertTrue(ref.reference_form is not None)
