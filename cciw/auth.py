import operator
from functools import reduce

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


WIKI_USERS_GROUP_NAME = 'Wiki users'
SECRETARY_GROUP_NAME = 'Secretaries'
LEADER_GROUP_NAME = 'Leaders'
COMMITTEE_GROUP_NAME = 'Committee'
BOOKING_SECRETARY_GROUP_NAME = 'Booking secretaries'

CAMP_ADMIN_GROUPS = [SECRETARY_GROUP_NAME, LEADER_GROUP_NAME, COMMITTEE_GROUP_NAME, BOOKING_SECRETARY_GROUP_NAME]

WIKI_GROUPS = [WIKI_USERS_GROUP_NAME, LEADER_GROUP_NAME, COMMITTEE_GROUP_NAME,
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
    for editing camp/officer/reference/CRB information
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


def is_committee_member(user):
    if not active_staff(user):
        return False
    return user_in_groups(user, [COMMITTEE_GROUP_NAME])
