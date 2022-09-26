from datetime import date, datetime, timedelta
from functools import lru_cache

from django.utils import timezone

from cciw.accounts.models import (
    BOOKING_SECRETARY_ROLE_NAME,
    DBS_OFFICER_ROLE_NAME,
    REFERENCE_CONTACT_ROLE_NAME,
    SECRETARY_ROLE_NAME,
    Role,
    User,
    setup_auth_roles,
)
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import set_thisyear
from cciw.contact_us.models import Message
from cciw.officers.models import Application, QualificationType, Referee, Reference
from cciw.utils.tests.factories import Auto, FactoriesBase, sequence

OFFICER_USERNAME = "joebloggs"
OFFICER_PASSWORD = "test_normaluser_password"
OFFICER_EMAIL = "joebloggs@somewhere.com"
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)


LEADER_USERNAME = "kevinsmith"
LEADER_PASSWORD = "test_normaluser_password"
LEADER_EMAIL = "leader@somewhere.com"
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)


BOOKING_SECRETARY_USERNAME = "bookingsec"
BOOKING_SECRETARY_PASSWORD = "a_password"
BOOKING_SECRETARY = (BOOKING_SECRETARY_USERNAME, BOOKING_SECRETARY_PASSWORD)


SECRETARY_USERNAME = "mrsecretary"
SECRETARY_PASSWORD = "test_password"
SECRETARY = (SECRETARY_USERNAME, SECRETARY_PASSWORD)


DBSOFFICER_USERNAME = "mrsdbsofficer"
DBSOFFICER_PASSWORD = "my_password"
DBSOFFICER_EMAIL = "dbsofficer@somewhere.com"
DBSOFFICER = (DBSOFFICER_USERNAME, DBSOFFICER_PASSWORD)


class CreateQualificationTypesMixin:
    def create_qualification_types(self) -> None:
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
            password=OFFICER_PASSWORD,
        )


class RolesSetupMixin:
    """
    Creates the basic Role objects that are expected to exist within the DB.
    """

    # This is normally done on deployment, so we can rely on
    # these Role objects existing in the database, like fixtures.

    def setUp(self):
        super().setUp()
        setup_auth_roles()


class OfficersSetupMixin(SimpleOfficerSetupMixin):
    """
    Sets up a suite of officers with correct permissions etc.
    """

    def setUp(self):
        super().setUp()
        self.leader_user = factories.create_leader(
            username=LEADER_USERNAME,
            first_name="Kevin",
            last_name="Smith",
            email=LEADER_EMAIL,
            password=LEADER_PASSWORD,
        )

        # Associate with Person object
        self.default_leader.users.add(self.leader_user)

        self.booking_secretary = factories.create_booking_secretary()
        self.secretary = factories.create_secretary()
        self.dbs_officer = factories.create_dbs_officer()
        self.safeguarding_coordinator = factories.create_safeguarding_coordinator()


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
    def create_default_applications(self) -> None:
        # Data: Applications 1 to 3 are in year 2000, for camps in summer 2000
        # Application 4 is for 2001
        self.application1 = factories.create_application(
            self.officer1,
            year=2000,
            referee2_overrides=dict(
                address="1267a Somewhere Road\r\nThereyougo",
                name="Mr Referee2 Name",
            ),
        )

        self.application2 = factories.create_application(
            self.officer2,
            year=2000,
            full_name="Peter Smith",
            referee1_overrides=dict(
                address="Referee 3 Address\r\nLine 2",
                email="referee3@email.co.uk",
                name="Mr Referee3 Name",
            ),
            referee2_overrides=dict(
                address="Referee 4 adddress",
                email="referee4@email.co.uk",
                name="Mr Referee4 Name",
            ),
        )

        self.application3 = factories.create_application(
            self.officer3,
            year=2000,
            full_name="Fred Jones",
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
            ),
        )

        # Application 4 is like 1 but a year later

        self.application4 = Application.objects.get(id=self.application1.id)
        self.application4.id = None  # force save as new
        self.application4.date_saved += timedelta(days=365)
        self.application4.save()

        # Dupe referee info:
        for r in self.application1.referees:
            self.application4.referee_set.create(referee_number=r.referee_number, name=r.name, email=r.email)


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


USERNAME_SEQUENCE = sequence(lambda n: f"auto_user_{n}")


class Factories(FactoriesBase):
    def create_officer(
        self,
        username: str = Auto,
        first_name: str = "Joe",
        last_name: str = "Bloggs",
        is_active: bool = True,
        is_superuser: bool = False,
        is_staff: bool = True,
        email: str = Auto,
        password: str = Auto,
        roles: list[Role] = Auto,
        contact_phone_number: str = "",
    ) -> User:
        username = username or next(USERNAME_SEQUENCE)
        email = email or f"{username}@example.com"

        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_superuser=is_superuser,
            is_staff=is_staff,
            email=email,
            contact_phone_number=contact_phone_number,
        )
        if password is Auto:
            password = OFFICER_PASSWORD
        if password is not None:
            user.set_password(password)
        user.save()
        if roles:
            user.roles.set(roles)
        return user

    def create_leader(self, **kwargs) -> User:
        # A leader is just an officer. No special roles are involved,
        # only the association to a camp via a `Person` record.
        return self.create_officer(**kwargs)

    @lru_cache
    def get_any_officer(self) -> User:
        user = User.objects.filter(is_staff=True).first()
        if not user:
            return self.create_officer()
        return user

    def add_officers_to_camp(self, camp: Camp, officers: list[User]) -> None:
        for officer in officers:
            camp.invitations.create(officer=officer)

    def _get_standard_role(self, name: str) -> Role:
        try:
            return Role.objects.get(name=name)
        except Role.DoesNotExist:
            # setup_auth_roles() is normally done on deployment, so we can rely
            # on these Role objects normally existing in the database, like
            # fixtures:
            setup_auth_roles()
            return Role.objects.get(name=name)

    def create_booking_secretary(self) -> User:
        return self.create_officer(
            username=BOOKING_SECRETARY_USERNAME,
            roles=[self._get_standard_role(BOOKING_SECRETARY_ROLE_NAME)],
            password=BOOKING_SECRETARY_PASSWORD,
        )

    def create_secretary(self) -> User:
        return self.create_officer(
            username=SECRETARY_USERNAME,
            roles=[self._get_standard_role(SECRETARY_ROLE_NAME)],
            password=SECRETARY_PASSWORD,
        )

    def create_dbs_officer(self) -> User:
        return self.create_officer(
            username=DBSOFFICER_USERNAME,
            email=DBSOFFICER_EMAIL,
            roles=[self._get_standard_role(DBS_OFFICER_ROLE_NAME)],
            password=DBSOFFICER_PASSWORD,
        )

    def create_safeguarding_coordinator(self) -> User:
        return self.create_officer(
            username="safeguarder",
            first_name="Safe",
            last_name="Guarder",
            contact_phone_number="01234 567890",
            roles=[self._get_standard_role(REFERENCE_CONTACT_ROLE_NAME)],
        )

    def create_application(
        self,
        officer: User = Auto,
        *,
        year: int = Auto,
        date_saved: date = Auto,
        full_name: str = Auto,
        address_firstline: str = Auto,
        birth_date: date = Auto,
        dbs_number: str = "",
        dbs_check_consent: bool = True,
        referee1_overrides: dict = Auto,
        referee2_overrides: dict = Auto,
        finished=True,
    ) -> Application:
        if date_saved is Auto:
            if year is not Auto:
                date_saved = datetime(year, 1, 1)
            else:
                date_saved = timezone.now().date()

        if officer is Auto:
            officer = self.get_any_officer()
        if full_name is Auto:
            full_name = "Joe Winston Bloggs"
        fields = dict(
            officer=officer,
            address_country="UK",
            address_county="Yorkshire",
            address_email="hey@boo.com",
            address_firstline="654 Stupid Way" if address_firstline is Auto else address_firstline,
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
            dbs_check_consent=dbs_check_consent,
            dbs_number=dbs_number,
            crime_declaration=False,
            crime_details="",
            date_saved=date_saved,
            finished=finished,
            full_name=full_name,
            illness_details="",
            relevant_illness=False,
            youth_experience="Lots",
            youth_work_declined=False,
            youth_work_declined_details="",
        )
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

    def create_complete_reference(self, referee: Referee) -> Reference:
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

    def create_contact_us_message(self) -> Message:
        return Message.objects.create(
            email="example@example.com",
            message="hello",
        )


factories = Factories()
