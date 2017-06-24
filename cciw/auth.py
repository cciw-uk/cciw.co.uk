from django.contrib.auth.backends import ModelBackend


class CciwAuthBackend(ModelBackend):
    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        # This makes /admin/officers/ return something for camp admins, rather
        # than a 403, and /admin/ return something rather than a message saying
        # there is nothing they can edit. This is necessary because, for
        # security reasons, we don't actually make camp admins/leaders part of a
        # specific group with permissions, but add overrides
        # (CampAdminPermissionMixin and other 'has_change_permission' methods)
        # to give specific permission to admin screens if the user is a camp
        # admin for a current camp. Doing it this way means we don't have to
        # remember to remove people from groups, it is all automatic.
        if user_obj.is_staff:
            if app_label == 'officers':
                if user_obj.can_manage_application_forms:
                    return True
            if app_label == 'cciwmain':
                if user_obj.can_edit_any_camps:
                    return True

        return super(CciwAuthBackend, self).has_module_perms(user_obj, app_label)
