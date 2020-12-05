from django.contrib.auth.backends import ModelBackend


class CciwAuthBackend(ModelBackend):
    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        # Our permission mechanisms for CCiW staff work like this:
        #
        # * We don't give normal Django admin permissions to users on an individual
        #   basis
        #
        # * We don't use membership of normal Django 'Group' for most users
        #   and for most roles (exceptions are in config/groups.yaml)
        #
        # * Instead, for many roles we dynamically work out a current "role"
        #   e.g. "camp leader" or "camp admin" - this means we don't need
        #   to remember to remove people from statically defined groups.
        #
        # To implement this, we use CampAdminPermissionMixin and override
        # other 'has_change_permission' methods, so we can allow specific people
        # access to specific modules, so that they can manage application forms,
        # for example, or view their own.
        #
        # The consequence of this is that many users appear to have no
        # admin permissions at all, or no permissions to a certain 'app' like
        # the 'officers' app. Because of this, for these users, due to the
        # assumptions made by Django admin, access to
        # /admin/ or /admin/officers/ would normally result in a 403.
        # or a page saying there is nothing they can edit.
        #
        # This class overrides that behaviour so that it applies our logic,
        # then fallbacks to normal logic if our exceptions don't apply.
        if user_obj.is_staff:
            if app_label == 'officers':
                if user_obj.can_manage_application_forms:
                    return True
            if app_label == 'cciwmain':
                if user_obj.can_edit_any_camps:
                    return True

        return super(CciwAuthBackend, self).has_module_perms(user_obj, app_label)
