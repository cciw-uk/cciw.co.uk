WIKI_USERS_GROUP_NAME = 'Wiki users'
SECRETARY_GROUP_NAME = 'Secretaries'
OFFICER_GROUP_NAME = 'Officers'
LEADER_GROUP_NAME = 'Leaders'


def is_camp_admin(user):
    """
    Returns True if the user is an admin for any camp, or has rights
    for editing camp/officer/reference/CRB information
    """
    return (user.groups.filter(name=LEADER_GROUP_NAME) |
            user.groups.filter(name=SECRETARY_GROUP_NAME)).exists() \
        or user.camps_as_admin.exists() > 0


def is_wiki_user(user):
    return user.groups.filter(name=WIKI_USERS_GROUP_NAME).exists()


def is_cciw_secretary(user):
    return user.groups.filter(name=SECRETARY_GROUP_NAME).exists()


def is_camp_officer(user):
    return (user.groups.filter(name=OFFICER_GROUP_NAME) |
            user.groups.filter(name=LEADER_GROUP_NAME)).exists()

