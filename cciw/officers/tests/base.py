from cciw.accounts.models import setup_auth_roles
from cciw.officers.models import QualificationType


class RequireQualificationTypesMixin:
    def setUp(self):
        super().setUp()
        self.first_aid_qualification, _ = QualificationType.objects.get_or_create(name="First Aid (1 day)")


class RolesSetupMixin:
    """
    Creates the basic Role objects that are expected to exist within the DB.
    """

    # This is normally done on deployment, so we can rely on
    # these Role objects existing in the database, like fixtures.

    def setUp(self):
        super().setUp()
        setup_auth_roles()
