import yaml
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils.functional import cached_property

# These names need to be synced with /config/groups.yaml
WIKI_USERS_GROUP_NAME = 'Wiki users'
SECRETARY_GROUP_NAME = 'Secretaries'
DBS_OFFICER_GROUP_NAME = 'DBS Officers'
COMMITTEE_GROUP_NAME = 'Committee'
BOOKING_SECRETARY_GROUP_NAME = 'Booking secretaries'
REFERENCE_CONTACT_GROUP_NAME = "Safeguarding co-ordinators"

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


def user_in_groups(user, group_names):
    if len(group_names) == 0:
        return False
    # We generally use this multiple times, so it is usually going to be much
    # faster to fetch and cache all the groups once if not already fetched.
    groups = None
    if hasattr(user, '_prefetched_objects_cache'):
        if 'groups' in user._prefetched_objects_cache:
            groups = user._prefetched_objects_cache['groups']
    else:
        user._prefetched_objects_cache = {}
    if groups is None:
        groups = user.groups.all()
        # Evaluate:
        list(groups)
        user._prefetched_objects_cache['groups'] = groups

    return any(g.name == name
               for name in group_names
               for g in groups)


def get_camp_admin_group_users():
    """
    Returns all users who are in the 'camp admin' groups.
    """
    return User.objects.filter(groups__in=Group.objects.filter(name__in=CAMP_ADMIN_GROUPS))


def get_group_users(group_name):
    return Group.objects.get(name=group_name).user_set.all()


def get_reference_contact_users():
    return get_group_users(REFERENCE_CONTACT_GROUP_NAME)


class User(AbstractUser):

    contact_phone_number = models.CharField("Phone number", max_length=40,
                                            blank=True,
                                            help_text="Required only for staff like CPO who need to be contacted.")

    def __str__(self):
        return "{0} <{1}>".format(self.full_name, self.email)

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name).strip()

    @cached_property
    def is_booking_secretary(user):
        if not active_staff(user):
            return False
        return user_in_groups(user, [BOOKING_SECRETARY_GROUP_NAME])

    @cached_property
    def is_camp_admin(self):
        """
        Returns True if the user is an admin for any camp, or has rights
        for editing camp/officer/reference/DBS information
        """
        if not active_staff(self):
            return False
        return user_in_groups(self, CAMP_ADMIN_GROUPS) or \
            len(self.current_camps_as_admin_or_leader) > 0

    @cached_property
    def is_potential_camp_officer(self):
        return active_staff(self)

    @cached_property
    def is_cciw_secretary(self):
        if not active_staff(self):
            return False
        return user_in_groups(self, [SECRETARY_GROUP_NAME])

    @cached_property
    def is_committee_member(self):
        if not active_staff(self):
            return False
        return user_in_groups(self, [COMMITTEE_GROUP_NAME])

    @cached_property
    def is_dbs_officer(self):
        if not active_staff(self):
            return False
        return user_in_groups(self, [DBS_OFFICER_GROUP_NAME])

    @cached_property
    def is_wiki_user(self):
        if not active_staff(self):
            return False
        return user_in_groups(self, WIKI_GROUPS)

    @cached_property
    def can_manage_application_forms(self):
        if self.has_perm('officers.change_application'):
            return True
        if self.is_camp_admin:
            return True
        if self.is_dbs_officer:
            return True
        return False

    @cached_property
    def can_edit_any_camps(self):
        if self.has_perm('cciwmain.change_camp'):
            return True
        # NB - only *current* camp leaders can edit any camp.
        # (past camp leaders are not assumed as responsible)
        if self.current_camps_as_admin_or_leader:
            return True
        return False

    def can_edit_camp(self, camp):
        # NB also editable_camps
        if self.has_perm('cciwmain.change_camp'):
            return True

        # We only allow current camps to be edited by
        # camp leaders, to avoid confusion and mistakes
        if (self.can_edit_any_camps and
                camp in self.current_camps_as_admin_or_leader):
            return True
        return False

    @cached_property
    def camps_as_admin_or_leader(self):
        """
        Returns all the camps for which the user is an admin or leader.
        """
        # If the user is am 'admin' for some camps:
        camps = self.camps_as_admin.all()
        # Find the 'Person' objects that correspond to this user
        leaders = list(self.people.all())
        # Find the camps for this leader
        # (We could do:
        #    Person.objects.get(user=user.id).camps_as_leader.all(),
        #  but we also must we handle the possibility that two Person
        #  objects have the same User objects, which could happen in the
        #  case where a leader leads by themselves and as part of a couple)
        for leader in leaders:
            camps = camps | leader.camps_as_leader.all()

        return camps.distinct()

    @cached_property
    def current_camps_as_admin_or_leader(self):
        from cciw.cciwmain import common

        return [c for c in self.camps_as_admin_or_leader
                if c.year == common.get_thisyear()]

    @cached_property
    def editable_camps(self):
        return self.current_camps_as_admin_or_leader

    @cached_property
    def can_search_officer_names(self):
        return (self.is_dbs_officer or
                self.is_committee_member or
                self.is_cciw_secretary or
                self.is_camp_admin)


def get_or_create_perm(app_label, model, codename):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    try:
        return Permission.objects.get(codename=codename, content_type=ct)
    except Permission.DoesNotExist:
        # This branch is generally only reached when running tests.
        return Permission.objects.create(codename=codename,
                                         name=codename,
                                         content_type=ct)


def setup_auth_groups():
    permissions_conf = yaml.load(open(settings.GROUPS_CONFIG_FILE), Loader=yaml.SafeLoader)
    groups = permissions_conf['Groups']
    for group_name, group_details in groups.items():
        g, _ = Group.objects.get_or_create(name=group_name)
        permission_details = group_details['Permissions']
        perms = []
        for p in permission_details:
            parts = p.split(',')
            perms.append(get_or_create_perm(*parts))
        with transaction.atomic():
            g.permissions.set(perms)
