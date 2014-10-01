import operator
from functools import reduce

WIKI_USERS_GROUP_NAME = 'Wiki users'
SECRETARY_GROUP_NAME = 'Secretaries'
OFFICER_GROUP_NAME = 'Officers'
LEADER_GROUP_NAME = 'Leaders'
BOOKING_SECRETARY_GROUP_NAME = 'Booking secretaries'

OFFICER_GROUPS = [OFFICER_GROUP_NAME, LEADER_GROUP_NAME]
CAMP_ADMIN_GROUPS = [SECRETARY_GROUP_NAME, LEADER_GROUP_NAME]

WIKI_GROUPS = [WIKI_USERS_GROUP_NAME, LEADER_GROUP_NAME,
               BOOKING_SECRETARY_GROUP_NAME, SECRETARY_GROUP_NAME]


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
    if not active_staff(user): return False
    return user_in_groups(user, CAMP_ADMIN_GROUPS) or \
        user.camps_as_admin.exists() > 0


def is_wiki_user(user):
    if not active_staff(user): return False
    return user_in_groups(user, WIKI_GROUPS)


def is_cciw_secretary(user):
    if not active_staff(user): return False
    return user_in_groups(user, [SECRETARY_GROUP_NAME])


def is_camp_officer(user):
    if not active_staff(user): return False
    return user_in_groups(user, OFFICER_GROUPS)


def is_booking_secretary(user):
    if not active_staff(user): return False
    return user_in_groups(user, [BOOKING_SECRETARY_GROUP_NAME])
