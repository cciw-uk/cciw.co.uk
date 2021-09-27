from django.contrib.auth import password_validation
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError

from cciw.accounts.models import User


class CciwAuthBackend:
    # This is similar to django.contrib.auth.backends.ModelBackend,
    # but based on our 'Role' instead of 'Group'. In addition, we also
    # drop "user permissions" (all permissions are defined at Role level).

    # We also include logic to check password against validators,
    # so that adding new validators causes people to change their
    # password after they login, if their password needs it.

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return
        try:
            user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            User().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                self.check_password_validation(user, password)
                return user

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        return user.is_active

    def _get_all_permissions(self, user_obj):
        if user_obj.is_superuser:
            perms = Permission.objects.all()
        else:
            perms = Permission.objects.filter(roles__members=user_obj)
        perms = perms.values_list("content_type__app_label", "codename").order_by()
        return {f"{ct}.{name}" for ct, name in perms}

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, "_perm_cache"):
            user_obj._perm_cache = self._get_all_permissions(user_obj)
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        return user_obj.is_active and (perm in self.get_all_permissions(user_obj, obj=obj))

    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        if user_obj.is_staff:
            # Our permission system uses a mix of:
            # * 'static' roles (DB defined) which uses permissions like the stock Django code,
            #    which makes
            #    get_all_permissions() return relevant permissions for Django admin.
            #
            # * other dynamic ones e.g. 'current camp leader', which do not
            #   contribute to get_all_permissions() (because the permissions
            #   would be too broad).
            #
            # We currently use CampAdminPermissionMixin and other overridden
            # `has_change_permission` methods to get the admin to allow users
            # without normal permissions to access limited parts of the admin.
            #
            # The consequence of this is that many users appear to have no admin
            # permissions at all (in terms of the result of
            # `get_all_permissions'), or no permissions to a certain 'app' like
            # the 'officers' app. Because of this, for these users, due to the
            # assumptions made by Django admin, access to /admin/ or
            # /admin/officers/ would normally result in a 403. or a page saying
            # there is nothing they can edit.
            #
            # We fix that up with these exceptions:
            if app_label == "officers":
                if user_obj.can_manage_application_forms:
                    return True
            if app_label == "cciwmain":
                if user_obj.can_edit_any_camps:
                    return True
        return user_obj.is_active and any(
            perm[: perm.index(".")] == app_label for perm in self.get_all_permissions(user_obj)
        )

    def check_password_validation(self, user, password):
        if not user.password_validation_needs_checking():
            return

        try:
            password_validation.validate_password(password, user=user)
        except ValidationError:
            user.mark_bad_password()
        else:
            user.clear_bad_password()
        user.save()
