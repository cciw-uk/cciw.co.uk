from cciw.accounts.models import BOOKING_SECRETARY_ROLE_NAME, CAMP_ADMIN_ROLES, SECRETARY_ROLE_NAME, user_has_role
from cciw.officers.tests.base import OFFICER, OfficersSetupMixin
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import WebTestBase


class TestUserModel(OfficersSetupMixin, TestBase):

    def test_user_in_group_true(self):
        with self.assertNumQueries(1):
            self.assertTrue(user_has_role(self.booking_secretary,
                                          [BOOKING_SECRETARY_ROLE_NAME]))

    def test_user_in_group_true_for_one_item(self):
        with self.assertNumQueries(1):
            self.assertTrue(user_has_role(self.booking_secretary,
                                          CAMP_ADMIN_ROLES))

    def test_user_in_group_false(self):
        with self.assertNumQueries(1):
            self.assertFalse(user_has_role(self.officer_user,
                                           [BOOKING_SECRETARY_ROLE_NAME]))

    def test_user_in_group_multiple_performance(self):
        with self.assertNumQueries(1):
            # 1 query
            self.assertFalse(user_has_role(self.officer_user,
                                           [BOOKING_SECRETARY_ROLE_NAME]))
        with self.assertNumQueries(0):
            # 0 query
            self.assertFalse(user_has_role(self.officer_user,
                                           [SECRETARY_ROLE_NAME]))
            self.assertFalse(self.officer_user.is_booking_secretary)

    def test_user_role_performance(self):
        with self.assertNumQueries(1):
            self.assertFalse(self.officer_user.is_booking_secretary)

        # Delete the cache established by 'cached_property;
        del self.officer_user.is_booking_secretary
        # and it should still require zero queries, because it uses
        # user_has_role
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


class TestSetPassword(OfficersSetupMixin, WebTestBase):
    def test_disallow_too_common(self):
        self.officer_login(OFFICER)
        self.get_url('admin:password_change')
        self.fill({
            '#id_old_password': OFFICER[1],
            '#id_new_password1': 'password',
            '#id_new_password2': 'password',
        })
        self.submit('[type=submit]')
        self.assertTextPresent('Your password can’t be a commonly used password.')

    def test_allow_good_password(self):
        self.officer_login(OFFICER)
        self.get_url('admin:password_change')
        new_password = 'Jo6Ohmieooque5A'
        self.fill({
            '#id_old_password': OFFICER[1],
            '#id_new_password1': new_password,
            '#id_new_password2': new_password,
        })
        self.submit('[type=submit]')
        self.assertTextPresent('Your password was changed')
        user = self.officer_user
        user.refresh_from_db()
        assert user.check_password(new_password)
