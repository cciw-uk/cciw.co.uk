from unittest.mock import patch

from django.urls import reverse
from furl import furl

from cciw.accounts.models import BOOKING_SECRETARY_ROLE_NAME, CAMP_MANAGER_ROLES, SECRETARY_ROLE_NAME, user_has_role
from cciw.officers.tests import factories
from cciw.utils.tests.base import TestBase
from cciw.utils.tests.webtest import WebTestBase


class TestUserModel(TestBase):
    def test_user_in_group_true(self):
        booking_secretary = factories.create_booking_secretary()
        with self.assertNumQueries(1):
            assert user_has_role(booking_secretary, [BOOKING_SECRETARY_ROLE_NAME])

    def test_user_in_group_true_for_one_item(self):
        booking_secretary = factories.create_booking_secretary()
        with self.assertNumQueries(1):
            assert user_has_role(booking_secretary, CAMP_MANAGER_ROLES)

    def test_user_in_group_false(self):
        officer_user = factories.create_officer()
        with self.assertNumQueries(1):
            assert not user_has_role(officer_user, [BOOKING_SECRETARY_ROLE_NAME])

    def test_user_in_group_multiple_performance(self):
        officer_user = factories.create_officer()
        with self.assertNumQueries(1):
            # 1 query
            assert not user_has_role(officer_user, [BOOKING_SECRETARY_ROLE_NAME])
        with self.assertNumQueries(0):
            # 0 query
            assert not user_has_role(officer_user, [SECRETARY_ROLE_NAME])
            assert not officer_user.is_booking_secretary

    def test_user_role_performance(self):
        officer_user = factories.create_officer()
        with self.assertNumQueries(1):
            assert not officer_user.is_booking_secretary

        # Delete the cache established by 'cached_property;
        del officer_user.is_booking_secretary
        # and it should still require zero queries, because it uses
        # user_has_role
        with self.assertNumQueries(0):
            assert not officer_user.is_booking_secretary

    def test_user_role_performance_2(self):
        officer_user = factories.create_officer()
        with self.assertNumQueries(1):
            # Testing multiple different roles requires just one query
            assert not officer_user.is_booking_secretary
            assert not officer_user.is_committee_member

    def test_has_perm(self):
        # Depends on static_roles.yaml
        booking_secretary = factories.create_booking_secretary()
        officer_user = factories.create_officer()
        assert booking_secretary.has_perm("bookings.add_booking")
        assert not officer_user.has_perm("bookings.add_booking")


class PwnedPasswordPatcherMixin:
    PWNED_PASSWORDS = ["pwnedpassword"]

    def setUp(self):
        super().setUp()
        self.pwned_password_patcher = patch("pwned_passwords_django.api.pwned_password", new=self.pwned_password)
        self.pwned_password_patcher.start()
        self.pwned_password_call_count = 0

    def tearDown(self):
        self.pwned_password_patcher.stop()
        super().tearDown()

    def pwned_password(self, password):
        self.pwned_password_call_count += 1
        return password in self.PWNED_PASSWORDS


class TestSetPassword(PwnedPasswordPatcherMixin, WebTestBase):

    good_password = "Jo6Ohmieooque5A"

    def test_disallow_too_common(self):
        self.officer_login(factories.create_officer(password="old"))
        self.get_url("admin:password_change")
        new_password = self.PWNED_PASSWORDS[0]
        self.fill(
            {
                "#id_old_password": "old",
                "#id_new_password1": new_password,
                "#id_new_password2": new_password,
            }
        )
        self.submit("[type=submit]")
        self.assertTextPresent("This password is too common.")

    def test_allow_good_password(self):
        self.officer_login(user := factories.create_officer(password="old"))
        self.get_url("admin:password_change")
        self.assertTextPresent("Use a password manager")
        new_password = self.good_password
        self.fill(
            {
                "#id_old_password": "old",
                "#id_new_password1": new_password,
                "#id_new_password2": new_password,
            }
        )
        self.submit("[type=submit]")
        self.assertTextPresent("Your password was changed")
        user.refresh_from_db()
        assert user.check_password(new_password)

    def test_handle_unvalidated_bad_password(self):
        # When we log in, if the password doesn't pass new validation checks,
        # we should require them to set their password.
        user = factories.create_officer()
        bad_password = self.PWNED_PASSWORDS[0]
        user.set_password(bad_password)
        user.mark_password_validation_not_done()
        user.save()

        self.get_url("cciw-officers-index")
        # We get redirected to login
        self.assertTextPresent("Password:")
        self.fill(
            {
                "#id_username": user.username,
                "#id_password": bad_password,
            }
        )
        self.submit("[type=submit]")

        assert self.pwned_password_call_count == 1
        user.refresh_from_db()

        # We should be redirected to set password page:
        assert furl(self.current_url).path == reverse("admin:password_change")

        # And there should be a specific reason
        self.assertTextPresent("Your current password doesn't meet our updated requirements")
        self.assertTextPresent("it may have been found on a list of compromised passwords.")
        self.assertTextPresent("Please choose a different password.")

        new_password = self.good_password
        self.fill(
            {
                "#id_old_password": bad_password,
                "#id_new_password1": new_password,
                "#id_new_password2": new_password,
            }
        )
        self.submit("[type=submit]")

        assert self.pwned_password_call_count == 2
        user.refresh_from_db()

        assert user.check_password(new_password)
        assert not user.password_validation_needs_checking()

        # finally should get back to where we were going
        assert furl(self.current_url).path == reverse("cciw-officers-index")

    def test_handle_unvalidated_good_password(self):
        # When we log in, if their password hasn't been checked, and it does
        # pass new validation checks, we shouldn't require them to set password
        # again.
        user = factories.create_officer(password=self.good_password)
        user.mark_password_validation_not_done()
        user.save()

        self.get_url("cciw-officers-index")
        self.fill(
            {
                "#id_username": user.username,
                "#id_password": self.good_password,
            }
        )
        self.submit("[type=submit]")
        assert self.pwned_password_call_count == 1

        assert furl(self.current_url).path == reverse("cciw-officers-index")
        user.refresh_from_db()
        assert not user.password_validation_needs_checking()

    def test_handle_validated_password(self):
        # When we log in, if their password has already been checked, we
        # shouldn't check it again.
        user = factories.create_officer(password=self.good_password)
        self.get_url("cciw-officers-index")
        self.fill(
            {
                "#id_username": user.username,
                "#id_password": self.good_password,
            }
        )
        self.submit("[type=submit]")
        assert furl(self.current_url).path == reverse("cciw-officers-index")
        assert self.pwned_password_call_count == 0
        user.refresh_from_db()
        assert not user.password_validation_needs_checking()
