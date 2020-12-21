from cciw.accounts.models import BOOKING_SECRETARY_GROUP_NAME, CAMP_ADMIN_GROUPS, SECRETARY_GROUP_NAME, user_in_groups
from cciw.officers.tests.base import OfficersSetupMixin
from cciw.utils.tests.base import TestBase


class TestUserModel(OfficersSetupMixin, TestBase):

    def test_user_in_group_true(self):
        with self.assertNumQueries(1):
            self.assertTrue(user_in_groups(self.booking_secretary,
                                           [BOOKING_SECRETARY_GROUP_NAME]))

    def test_user_in_group_true_for_one_item(self):
        with self.assertNumQueries(1):
            self.assertTrue(user_in_groups(self.booking_secretary,
                                           CAMP_ADMIN_GROUPS))

    def test_user_in_group_false(self):
        with self.assertNumQueries(1):
            self.assertFalse(user_in_groups(self.officer_user,
                                            [BOOKING_SECRETARY_GROUP_NAME]))

    def test_user_in_group_multiple_performance(self):
        with self.assertNumQueries(1):
            # 1 query
            self.assertFalse(user_in_groups(self.officer_user,
                                            [BOOKING_SECRETARY_GROUP_NAME]))
        with self.assertNumQueries(0):
            # 0 query
            self.assertFalse(user_in_groups(self.officer_user,
                                            [SECRETARY_GROUP_NAME]))
            self.assertFalse(self.officer_user.is_booking_secretary)

    def test_user_role_performance(self):
        with self.assertNumQueries(1):
            self.assertFalse(self.officer_user.is_booking_secretary)

        # Delete the cache established by 'cached_property;
        del self.officer_user.is_booking_secretary
        # and it should still require zero queries, because it uses
        # user_in_groups
        with self.assertNumQueries(0):
            self.assertFalse(self.officer_user.is_booking_secretary)

    def test_user_role_performance_2(self):
        with self.assertNumQueries(1):
            # Testing multiple different roles requires just one query
            self.assertFalse(self.officer_user.is_booking_secretary)
            self.assertFalse(self.officer_user.is_committee_member)

    def test_has_perm(self):
        # Depends on static_roles.yaml
        assert self.booking_secretary.has_perm('bookings.add_booking')
        assert not self.officer_user.has_perm('bookings.add_booking')
