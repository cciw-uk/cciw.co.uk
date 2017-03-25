import operator
from functools import reduce

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group

WIKI_USERS_GROUP_NAME = 'Wiki users'
SECRETARY_GROUP_NAME = 'Secretaries'
COMMITTEE_GROUP_NAME = 'Committee'
BOOKING_SECRETARY_GROUP_NAME = 'Booking secretaries'

CAMP_ADMIN_GROUPS = [SECRETARY_GROUP_NAME, COMMITTEE_GROUP_NAME, BOOKING_SECRETARY_GROUP_NAME]

WIKI_GROUPS = [WIKI_USERS_GROUP_NAME, COMMITTEE_GROUP_NAME,
               BOOKING_SECRETARY_GROUP_NAME, SECRETARY_GROUP_NAME]


# TODO:
# We need better terminology to distinguish:
# 1) users designated as 'admin' for a camp
# 2) users with admin rights for a camp (includes 1. above and leaders)
# 3) users with general admin rights (includes committee, secretaries)

def active_staff(user):
    return user.is_staff and user.is_active


def user_in_groups(user, groups):
    if len(groups) == 0:
        return False
    return reduce(operator.or_,
                  [user.groups.filter(name=g) for g in groups]).exists()


def is_camp_admin(user):
    """
    Returns True if the user is an admin for any camp, or has rights
    for editing camp/officer/reference/DBS information
    """
    if not active_staff(user):
        return False
    return user_in_groups(user, CAMP_ADMIN_GROUPS) or \
        len(user.current_camps_as_admin_or_leader) > 0


def get_camp_admin_group_users():
    """
    Returns all users who are in the 'camp admin' groups.
    """
    User = get_user_model()
    return User.objects.filter(groups__in=Group.objects.filter(name__in=CAMP_ADMIN_GROUPS))


def get_group_users(group_name):
    return Group.objects.get(name=group_name).user_set.all()


def is_wiki_user(user):
    if not active_staff(user):
        return False
    return user_in_groups(user, WIKI_GROUPS)


def is_cciw_secretary(user):
    if not active_staff(user):
        return False
    return user_in_groups(user, [SECRETARY_GROUP_NAME])


def is_camp_officer(user):
    return active_staff(user)


def is_booking_secretary(user):
    if not active_staff(user):
        return False
    return user_in_groups(user, [BOOKING_SECRETARY_GROUP_NAME])


def can_manage_application_forms(user):
    if user.has_perm('officers.change_application'):
        return True
    if is_camp_admin(user):
        return True
    return False


def can_edit_any_camps(user):
    if user.has_perm('cciwmain.change_camp'):
        return True
    # NB - only *current* camp leaders can edit any camp.
    # (past camp leaders are not assumed as responsible)
    if user.current_camps_as_admin_or_leader:
        return True
    return False


def can_edit_camp(user, camp):
    # NB also editable_camps
    if user.has_perm('cciwmain.change_camp'):
        return True

    # We only allow current camps to be edited by
    # camp leaders, to avoid confusion and mistakes
    if (can_edit_any_camps(user) and
            camp in user.current_camps_as_admin_or_leader):
        return True
    return False


def editable_camps(user):
    return user.current_camps_as_admin_or_leader


def is_committee_member(user):
    if not active_staff(user):
        return False
    return user_in_groups(user, [COMMITTEE_GROUP_NAME])


class CciwAuthBackend(ModelBackend):
    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        # This makes /admin/officers/ return something for camp admins, rather
        # than a 403, and /admin/ return something rather than a message saying
        # there is nothing they can edit. This is necessary because, for
        # security reasons, we don't actually make camp admins/leaders part of a
        # specific group with permissions, but add hacks
        # (CampAdminPermissionMixin and other 'has_change_permission' methods)
        # to give specific permission to admin screens if the user is a camp
        # admin for a current camp. Doing it this way means we don't have to
        # remember to remove people from groups, it is all automatic.
        if app_label == 'officers':
            if can_manage_application_forms(user_obj):
                return True
        if app_label == 'cciwmain':
            if can_edit_any_camps(user_obj):
                return True

        return super(CciwAuthBackend, self).has_module_perms(user_obj, app_label)
