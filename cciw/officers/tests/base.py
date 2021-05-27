from datetime import date, datetime, timedelta
from functools import lru_cache

from django.utils import timezone

from cciw.accounts.models import (BOOKING_SECRETARY_ROLE_NAME, DBS_OFFICER_ROLE_NAME, REFERENCE_CONTACT_ROLE_NAME,
                                  SECRETARY_ROLE_NAME, Role, User, setup_auth_roles)
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import set_thisyear
from cciw.contact_us.models import Message
from cciw.officers.models import Application, QualificationType, Reference
from cciw.utils.tests.base import FactoriesBase

OFFICER_USERNAME = 'joebloggs'
OFFICER_PASSWORD = 'test_normaluser_password'
OFFICER_EMAIL = "joebloggs@somewhere.com"
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)


LEADER_USERNAME = 'kevinsmith'
LEADER_PASSWORD = 'test_normaluser_password'
LEADER_EMAIL = 'leader@somewhere.com'
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)


BOOKING_SECRETARY_USERNAME = 'bookingsec'
BOOKING_SECRETARY_PASSWORD = 'a_password'
BOOKING_SECRETARY = (BOOKING_SECRETARY_USERNAME, BOOKING_SECRETARY_PASSWORD)


SECRETARY_USERNAME = 'mrsecretary'
SECRETARY_PASSWORD = 'test_password'
SECRETARY = (SECRETARY_USERNAME, SECRETARY_PASSWORD)


DBSOFFICER_USERNAME = 'mrsdbsofficer'
DBSOFFICER_PASSWORD = 'my_password'
DBSOFFICER_EMAIL = 'dbsofficer@somewhere.com'
DBSOFFICER = (DBSOFFICER_USERNAME, DBSOFFICER_PASSWORD)


class CreateQualificationTypesMixin(object):
    def create_qualification_types(self):
        self.first_aid_qualification, _ = QualificationType.objects.get_or_create(name="First Aid (1 day)")


class RequireQualificationTypesMixin(CreateQualificationTypesMixin):
    def setUp(self):
        super().setUp()
        self.create_qualification_types()


class SimpleOfficerSetupMixin(BasicSetupMixin):
    """
    Sets up a single officer with minimal permissions
    """
    def setUp(self):
        super().setUp()
        self.officer_user = factories.create_officer(
            username=OFFICER_USERNAME,
            first_name="Joe",
            last_name="Bloggs",
            email=OFFICER_EMAIL,
            password=OFFICER_PASSWORD
        )


class OfficersSetupMixin(SimpleOfficerSetupMixin):
    """
    Sets up a suite of officers with correct permissions etc.
    """
    def setUp(self):
        super().setUp()
        setup_auth_roles()
        self.leader_user = factories.create_officer(
            username=LEADER_USERNAME,
            first_name="Kevin",
            last_name="Smith",
            email=LEADER_EMAIL,
            password=LEADER_PASSWORD,
        )

        # Associate with Person object
        self.default_leader.users.add(self.leader_user)

        self.booking_secretary_role = Role.objects.get(name=BOOKING_SECRETARY_ROLE_NAME)
        self.booking_secretary = factories.create_officer(
            username=BOOKING_SECRETARY_USERNAME,
            roles=[self.booking_secretary_role],
            password=BOOKING_SECRETARY_PASSWORD,
        )

        self.secretary_role = Role.objects.get(name=SECRETARY_ROLE_NAME)
        self.secretary = factories.create_officer(
            username=SECRETARY_USERNAME,
            roles=[self.secretary_role],
            password=SECRETARY_PASSWORD,
        )

        self.dbs_officer_group = Role.objects.get(name=DBS_OFFICER_ROLE_NAME)
        self.dbs_officer = factories.create_officer(
            username=DBSOFFICER_USERNAME,
            email=DBSOFFICER_EMAIL,
            roles=[self.dbs_officer_group],
            password=DBSOFFICER_PASSWORD,
        )

        self.reference_contact_group = Role.objects.get(name=REFERENCE_CONTACT_ROLE_NAME)
        self.safeguarding_coordinator = factories.create_officer(
            username="safeguarder",
            first_name="Safe",
            last_name="Guarder",
            contact_phone_number="01234 567890",
            roles=[self.reference_contact_group],
        )


class ExtraOfficersSetupMixin(OfficersSetupMixin):
    """
    Sets up a set of normal officers who are on camp lists,
    along with those created by OfficersSetupMixin
    """

    def setUp(self):
        super().setUp()

        self.officer1 = self.officer_user
        self.officer2 = factories.create_officer(
            username="petersmith",
            first_name="Peter",
            last_name="Smith",
            email="petersmith@somewhere.com",
        )

        self.officer3 = factories.create_officer(
            username="fredjones",
            first_name="Fred",
            last_name="Jones",
            email="fredjones@somewhere.com",
        )

        self.default_camp_1.invitations.create(officer=self.officer1)
        self.default_camp_1.invitations.create(officer=self.officer2)
        self.default_camp_1.invitations.create(officer=self.officer3)


class DefaultApplicationsMixin(ExtraOfficersSetupMixin):

    def create_default_applications(self):
        # Data: Applications 1 to 3 are in year 2000, for camps in summer 2000
        # Application 4 is for 2001
        self.application1 = factories.create_application(
            self.officer1, year=2000,
            referee2_overrides=dict(
                address="1267a Somewhere Road\r\nThereyougo",
                name="Mr Referee2 Name",
            ))

        self.application2 = factories.create_application(
            self.officer2, year=2000,
            overrides=dict(
                full_name="Peter Smith",
            ),
            referee1_overrides=dict(
                address="Referee 3 Address\r\nLine 2",
                email="referee3@email.co.uk",
                name="Mr Referee3 Name",
            ),
            referee2_overrides=dict(
                address="Referee 4 adddress",
                email="referee4@email.co.uk",
                name="Mr Referee4 Name",
            ))

        self.application3 = factories.create_application(
            self.officer3, year=2000,
            overrides=dict(
                full_name="Fred Jones",
            ),
            referee1_overrides=dict(
                address="Referee 5 Address\r\nLine 2",
                email="referee5@email.co.uk",
                name="Mr Refere5 Name",
            ),
            referee2_overrides=dict(
                address="Referee 6 adddress",
                email="",
                name="Mr Referee6 Name",
                tel="01234 567890",
            ))

        # Application 4 is like 1 but a year later

        self.application4 = Application.objects.get(id=self.application1.id)
        self.application4.id = None  # force save as new
        self.application4.date_saved += timedelta(days=365)
        self.application4.save()

        # Dupe referee info:
        for r in self.application1.referees:
            self.application4.referee_set.create(
                referee_number=r.referee_number,
                name=r.name,
                email=r.email)


class RequireApplicationsMixin(DefaultApplicationsMixin):
    def setUp(self):
        super().setUp()
        self.create_default_applications()


class CurrentCampsMixin(BasicSetupMixin):
    def setUp(self):
        super().setUp()
        # Make sure second camp has end date in future, otherwise we won't be able to
        # save. Previous camp should be one year earlier i.e in the past
        self.default_camp_1.start_date = date.today() + timedelta(100 - 365)
        self.default_camp_1.end_date = date.today() + timedelta(107 - 365)
        self.default_camp_1.save()
        self.default_camp_2.start_date = date.today() + timedelta(100)
        self.default_camp_2.end_date = date.today() + timedelta(107)
        self.default_camp_2.save()


class ReferenceSetupMixin(set_thisyear(2000), RequireApplicationsMixin):

    def setUp(self):
        super().setUp()
        self.reference1_1 = factories.create_complete_reference(self.application1.referees[0])
        self.application1.referees[1].log_request_made(None, timezone.now())
        self.application2.referees[1].log_request_made(None, timezone.now())


class Factories(FactoriesBase):
    def __init__(self):
        self._user_counter = 0

    def create_officer(
            self,
            username=None,
            first_name='Joe',
            last_name='Bloggs',
            is_active=True,
            is_superuser=False,
            is_staff=True,
            email=None,
            password=None,
            roles=None,
            contact_phone_number='',
    ):
        username = username or self._make_auto_username()
        email = email or self._make_auto_email(username)
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_superuser=is_superuser,
            is_staff=is_staff,
            email=email,
            contact_phone_number=contact_phone_number,
        )
        if password:
            user.set_password(password)
            user.save()
        if roles:
            user.roles.set(roles)
        return user

    @lru_cache()
    def get_any_officer(self):
        user = User.objects.filter(is_staff=True).first()
        if not user:
            return self.create_officer()
        return user

    def _make_auto_username(self):
        self._user_counter += 1
        return f'auto_user_{self._user_counter}'

    def _make_auto_email(self, username=None):
        username = username or self._make_auto_username()
        return f'{username}@example.com'

    def add_officers_to_camp(self, camp, officers):
        for officer in officers:
            camp.invitations.create(officer=officer)

    def create_application(self, officer, *,
                           year=None,
                           date_saved=None,
                           full_name=None,
                           address_firstline=None,
                           birth_date=None,
                           overrides=None,
                           referee1_overrides=None,
                           referee2_overrides=None):
        if year is not None:
            date_saved = datetime(year, 3, 1)
        elif date_saved is None:
            date_saved = timezone.now().date()

        fields = dict(
            officer=officer,
            address_country="UK",
            address_county="Yorkshire",
            address_email="hey@boo.com",
            address_firstline="654 Stupid Way" if address_firstline is None else address_firstline,
            address_mobile="",
            address_postcode="XY9 8WN",
            address_tel="01048378569",
            address_town="Bradford",
            allegation_declaration=False,
            birth_date=birth_date or "1911-02-07",
            birth_place="Foobar",
            christian_experience="Became a Christian at age 0.2 years",
            concern_declaration=False,
            concern_details="",
            court_declaration=False,
            court_details="",
            dbs_check_consent=True,
            dbs_number="",
            crime_declaration=False,
            crime_details="",
            date_saved=date_saved,
            finished=True,
            full_name="Joe Winston Bloggs" if full_name is None else full_name,
            illness_details="",
            relevant_illness=False,
            youth_experience="Lots",
            youth_work_declined=False,
            youth_work_declined_details="",
        )
        if overrides:
            fields.update(overrides)
        application = Application.objects.create(**fields)
        for referee_number, ref_overrides in zip([1, 2], [referee1_overrides, referee2_overrides]):
            referee_fields = dict(
                referee_number=referee_number,
                address=f"Referee {referee_number} Address\r\nLine 2",
                email=f"referee{referee_number}@email.co.uk",
                mobile="",
                name=f"Referee{referee_number} Name",
                tel="01222 666666",
            )
            if ref_overrides:
                referee_fields.update(ref_overrides)

            application.referee_set.create(**referee_fields)
        return application

    def create_complete_reference(self, referee):
        return Reference.objects.create(
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

    def create_contact_us_message(self):
        return Message.objects.create(
            email='example@example.com',
            message='hello',
        )


factories = Factories()
