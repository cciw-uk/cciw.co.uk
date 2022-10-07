from cciw.accounts.models import setup_auth_roles
from cciw.officers.models import QualificationType

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

# A lot of this stuff should be rewritten as per https://github.com/cciw-uk/cciw.co.uk/issues/6

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


class RolesSetupMixin:
    """
    Creates the basic Role objects that are expected to exist within the DB.
    """

    # This is normally done on deployment, so we can rely on
    # these Role objects existing in the database, like fixtures.

    def setUp(self):
        super().setUp()
        setup_auth_roles()
