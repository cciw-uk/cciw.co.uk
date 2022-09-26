from datetime import date, timedelta

from django.utils import timezone

from cciw.accounts.models import setup_auth_roles
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import SetThisYearMixin
from cciw.officers.models import Application, QualificationType

from . import factories
from .factories import (  # noqa: F401
    BOOKING_SECRETARY,
    BOOKING_SECRETARY_PASSWORD,
    BOOKING_SECRETARY_USERNAME,
    DBSOFFICER,
    DBSOFFICER_EMAIL,
    DBSOFFICER_PASSWORD,
    DBSOFFICER_USERNAME,
    SECRETARY,
    SECRETARY_PASSWORD,
    SECRETARY_USERNAME,
)

# A lot of this stuff should be rewritten as per https://gitlab.com/cciw/cciw.co.uk/-/issues/6

# Then we wouldn't need all these constants. Plus we shouldn't need passwords
# due to improvements in django_functest shortcut_login

OFFICER_USERNAME = "joebloggs"
OFFICER_PASSWORD = "test_normaluser_password"
OFFICER_EMAIL = "joebloggs@somewhere.com"
OFFICER = (OFFICER_USERNAME, OFFICER_PASSWORD)


LEADER_USERNAME = "kevinsmith"
LEADER_PASSWORD = "test_normaluser_password"
LEADER_EMAIL = "leader@somewhere.com"
LEADER = (LEADER_USERNAME, LEADER_PASSWORD)


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


class ReferenceSetupMixin(SetThisYearMixin, RequireApplicationsMixin):
    thisyear = 2000

    def setUp(self):
        super().setUp()
        self.reference1_1 = factories.create_complete_reference(self.application1.referees[0])
        self.application1.referees[1].log_request_made(None, timezone.now())
        self.application2.referees[1].log_request_made(None, timezone.now())
