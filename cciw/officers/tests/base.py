from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

from django_dynamic_fixture import G

from cciw.auth import BOOKING_SECRETARY_GROUP_NAME, LEADER_GROUP_NAME, OFFICER_GROUP_NAME
from cciw.cciwmain.tests.base import BasicSetupMixin


OFFICER_USERNAME = 'mrofficer2'
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
        self.officers_group = G(Group,
                                name=OFFICER_GROUP_NAME,
                                permissions=[])

        self.officer_user = G(User,
                              username=OFFICER_USERNAME,
                              is_active=True,
                              is_superuser=False,
                              is_staff=True,
                              groups=[self.officers_group],
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
                                        "auth",
                                        "user"),
                                   perm("change_user",
                                        "auth",
                                        "user"),
                                   perm("delete_user",
                                        "auth",
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
