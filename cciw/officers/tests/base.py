from datetime import timedelta, datetime, date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django_dynamic_fixture import G
from django.utils import timezone

from cciw.auth import BOOKING_SECRETARY_GROUP_NAME, LEADER_GROUP_NAME
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.officers.models import Application, Reference

User = get_user_model()

OFFICER_USERNAME = 'joebloggs'
OFFICER_PASSWORD = 'test_normaluser_password'
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)


LEADER_USERNAME = 'davestott'
LEADER_PASSWORD = 'test_normaluser_password'
LEADER_EMAIL = 'leader@somewhere.com'
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)


BOOKING_SEC_USERNAME = 'booker'
BOOKING_SEC_PASSWORD = 'test_normaluser_password'
BOOKING_SEC = (BOOKING_SEC_USERNAME, BOOKING_SEC_PASSWORD)


def perm(codename, app_label, model):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    try:
        return Permission.objects.get(codename=codename, content_type=ct)
    except Permission.DoesNotExist:
        return G(Permission,
                 codename=codename,
                 content_type=ct)


class OfficersSetupMixin(BasicSetupMixin):
    def setUp(self):
        super(OfficersSetupMixin, self).setUp()
        self.officer_user = G(User,
                              username=OFFICER_USERNAME,
                              first_name="Joe",
                              last_name="Bloggs",
                              is_active=True,
                              is_superuser=False,
                              is_staff=True,
                              permissions=[])
        self.officer_user.set_password(OFFICER_PASSWORD)
        self.officer_user.save()

        self.leaders_group = G(Group,
                               name=LEADER_GROUP_NAME,
                               permissions=[
                                   perm("add_application",
                                        "officers",
                                        "application"),
                                   perm("change_application",
                                        "officers",
                                        "application"),
                                   perm("delete_application",
                                        "officers",
                                        "application"),
                                   perm("change_camp",
                                        "cciwmain",
                                        "camp"),
                                   perm("add_person",
                                        "cciwmain",
                                        "person"),
                                   perm("change_person",
                                        "cciwmain",
                                        "person"),
                                   perm("delete_person",
                                        "cciwmain",
                                        "person"),
                                   perm("add_reference",
                                        "officers",
                                        "reference"),
                                   perm("change_reference",
                                        "officers",
                                        "reference"),
                                   perm("delete_reference",
                                        "officers",
                                        "reference"),
                                   perm("add_user",
                                        "accounts",
                                        "user"),
                                   perm("change_user",
                                        "accounts",
                                        "user"),
                                   perm("delete_user",
                                        "accounts",
                                        "user")
                               ],
                               )

        self.leader_user = G(User,
                             username=LEADER_USERNAME,
                             first_name="Dave",
                             last_name="Stott",
                             is_active=True,
                             is_superuser=False,
                             is_staff=True,
                             email=LEADER_EMAIL,
                             groups=[self.leaders_group],
                             permissions=[])
        self.leader_user.set_password(LEADER_PASSWORD)
        self.leader_user.save()

        # Associate with Person object
        self.default_leader.users.add(self.leader_user)

        self.booking_secretary_group = G(Group,
                                         name=BOOKING_SECRETARY_GROUP_NAME,
                                         permissions=[
                                             perm("add_booking",
                                                  "bookings",
                                                  "booking"),
                                             perm("change_booking",
                                                  "bookings",
                                                  "booking"),
                                             perm("delete_booking",
                                                  "bookings",
                                                  "booking"),
                                             perm("add_bookingaccount",
                                                  "bookings",
                                                  "bookingaccount"),
                                             perm("change_bookingaccount",
                                                  "bookings",
                                                  "bookingaccount"),
                                         ],
                                         )

        self.booking_secretary = G(User,
                                   username=BOOKING_SEC_USERNAME,
                                   is_active=True,
                                   is_superuser=False,
                                   is_staff=True,
                                   groups=[self.booking_secretary_group])
        self.booking_secretary.set_password(BOOKING_SEC_PASSWORD)
        self.booking_secretary.save()


class ExtraOfficersSetupMixin(OfficersSetupMixin):

    def setUp(self):
        super(ExtraOfficersSetupMixin, self).setUp()

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

        self.default_camp_1.invitations.create(officer=self.officer1)
        self.default_camp_1.invitations.create(officer=self.officer2)
        self.default_camp_1.invitations.create(officer=self.officer3)


class ApplicationSetupMixin(ExtraOfficersSetupMixin):

    def setUp(self):
        super(ApplicationSetupMixin, self).setUp()

        # Data: Applications 1 to 3 are in year 2000, for camps in summer 2000
        # Application 4 is for 2001

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
                              date_submitted=datetime(2000, 3, 1),
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
                              relevant_illness=False,
                              youth_experience="Lots",
                              youth_work_declined=False,
                              youth_work_declined_details="",
                              )
        self.application1.referee_set.create(
            referee_number=1,
            address="Referee 1 Address\r\nLine 2",
            email="referee1@email.co.uk",
            mobile="",
            name="Referee1 Name",
            tel="01222 666666",
        )
        self.application1.referee_set.create(
            referee_number=2,
            address="1267a Somewhere Road\r\nThereyougo",
            email="referee2@email.co.uk",
            mobile="",
            name="Mr Referee2 Name",
            tel="01234 567890",
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
                              date_submitted=datetime(2000, 3, 1),
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
                              relevant_illness=False,
                              youth_experience="Lots",
                              youth_work_declined=False,
                              youth_work_declined_details="",
                              )

        self.application2.referee_set.create(
            referee_number=1,
            address="Referee 3 Address\r\nLine 2",
            email="referee3@email.co.uk",
            mobile="",
            name="Mr Referee3 Name",
            tel="01222 666666",
        )
        self.application2.referee_set.create(
            referee_number=2,
            address="Referee 4 adddress",
            email="referee4@email.co.uk",
            mobile="",
            name="Mr Referee4 Name",
            tel="01234 567890",
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
                              date_submitted=datetime(2000, 3, 1),
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
                              relevant_illness=False,
                              youth_experience="Lots",
                              youth_work_declined=False,
                              youth_work_declined_details="",
                              )

        self.application3.referee_set.create(
            referee_number=1,
            address="Referee 5 Address\r\nLine 2",
            email="referee5@email.co.uk",
            mobile="",
            name="Mr Refere5 Name",
            tel="01222 666666",
        ),
        self.application3.referee_set.create(
            referee_number=2,
            address="Referee 6 adddress",
            email="",
            mobile="",
            name="Mr Referee6 Name",
            tel="01234 567890",
        )

        # Application 4 is like 1 but a year later

        self.application4 = Application.objects.get(id=self.application1.id)
        self.application4.id = None  # force save as new
        self.application4.date_submitted += timedelta(days=365)
        self.application4.save()

        # Dupe referee info:
        for r in self.application1.referees:
            self.application4.referee_set.create(
                referee_number=r.referee_number,
                name=r.name,
                email=r.email)


class ReferenceHelperMixin(object):

    def create_complete_reference(self, referee):
        return G(Reference,
                 referee=referee,
                 referee_name="Referee1 Name",
                 how_long_known="A long time",
                 capacity_known="Pastor",
                 known_offences=False,
                 capability_children="Wonderful",
                 character="Almost sinless",
                 concerns="Perhaps too good for camp",
                 comments="",
                 date_created=datetime(2000, 2, 20),
                 )


class ReferenceSetupMixin(ReferenceHelperMixin, ApplicationSetupMixin):

    def setUp(self):
        super(ReferenceSetupMixin, self).setUp()
        self.reference1_1 = self.create_complete_reference(self.application1.referees[0])
        self.application1.referees[1].log_request_made(None, timezone.now())
        self.application2.referees[1].log_request_made(None, timezone.now())


class CurrentCampsMixin(object):
    def setUp(self):
        super(CurrentCampsMixin, self).setUp()
        # Make sure second camp has end date in future, otherwise we won't be able to
        # save. Previous camp should be one year earlier i.e in the past
        self.default_camp_1.start_date = date.today() + timedelta(100 - 365)
        self.default_camp_1.end_date = date.today() + timedelta(107 - 365)
        self.default_camp_1.save()
        self.default_camp_2.start_date = date.today() + timedelta(100)
        self.default_camp_2.end_date = date.today() + timedelta(107)
        self.default_camp_2.save()
