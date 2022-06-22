"""
User accounts for staff
"""
import logging

import yaml
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import AbstractBaseUser, Permission
from django.contrib.auth.models import UserManager as UserManagerDjango
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property

# These names need to be synced with /config/static_roles.yaml
WIKI_USERS_ROLE_NAME = "Wiki users"
SECRETARY_ROLE_NAME = "Secretaries"
DBS_OFFICER_ROLE_NAME = "DBS Officers"
COMMITTEE_ROLE_NAME = "Committee"
BOOKING_SECRETARY_ROLE_NAME = "Booking secretaries"
REFERENCE_CONTACT_ROLE_NAME = "Safeguarding co-ordinators"

CAMP_MANAGER_ROLES = [SECRETARY_ROLE_NAME, COMMITTEE_ROLE_NAME, BOOKING_SECRETARY_ROLE_NAME]

WIKI_ROLES = [WIKI_USERS_ROLE_NAME, COMMITTEE_ROLE_NAME, BOOKING_SECRETARY_ROLE_NAME, SECRETARY_ROLE_NAME]


# TODO:
# We need better terminology to distinguish:
# 1) users designated as 'admin' for a camp
# 2) users with admin rights for a camp (includes 1. above and leaders)
# 3) users with general admin rights (includes committee, secretaries)


logger = logging.getLogger(__name__)


def active_staff(user):
    return user.is_staff and user.is_active


def user_has_role(user, role_names):
    if len(role_names) == 0:
        return False
    # We generally use this multiple times, so it is usually going to be much
    # faster to fetch and cache all the roles once if not already fetched.
    roles = None
    if hasattr(user, "_prefetched_objects_cache"):
        if "roles" in user._prefetched_objects_cache:
            roles = user._prefetched_objects_cache["roles"]
    else:
        user._prefetched_objects_cache = {}
    if roles is None:
        roles = user.roles.all()
        # Evaluate:
        list(roles)
        user._prefetched_objects_cache["roles"] = roles

    return any(role.name == name for name in role_names for role in roles)


def get_camp_manager_role_users():
    """
    Returns all users who are in the 'camp admin' roles
    """
    return User.objects.filter(roles__in=Role.objects.filter(name__in=CAMP_MANAGER_ROLES))


def get_role_users(role_name):
    return Role.objects.get(name=role_name).members.all()


def get_role_email_recipients(role_name):
    return Role.objects.get(name=role_name).email_recipients.all()


def get_reference_contact_users():
    users = get_role_users(REFERENCE_CONTACT_ROLE_NAME)
    for user in users:
        if not user.contact_phone_number:
            logger.error("No contact_phone_number defined for reference contact user %s id %s", user.username, user.id)
    return users


class UserQuerySet(models.QuerySet):
    def older_than(self, before_datetime):
        return self.filter(date_joined__lt=before_datetime)


class UserManager(UserManagerDjango.from_queryset(UserQuerySet)):
    pass


# Our model is similar to AbstractUser, but our permissions are a bit different:
# we don't have user level permissions, and we have our custom 'Role' instead of
# 'Group' (and the M2M is on Role instead of User). So we inherit from
# AbstractBaseUser instead, and copy-paste some fields and methods


class User(AbstractBaseUser):
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
        validators=[username_validator],
        error_messages={
            "unique": "A user with that username already exists.",
        },
    )
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField("email address", blank=True)
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active. "
        "Unselect this instead of deleting accounts.",
    )
    date_joined = models.DateTimeField(default=timezone.now)
    is_superuser = models.BooleanField(
        "superuser status",
        default=False,
        help_text="Designates that this user has all permissions without " "explicitly assigning them.",
    )

    contact_phone_number = models.CharField(
        "Phone number",
        max_length=40,
        blank=True,
        help_text="Required only for staff like CPO who need to be contacted.",
    )

    bad_password = models.BooleanField(default=False)
    password_validators_used = models.TextField(blank=True)

    erased_on = models.DateTimeField(null=True, blank=True, default=None)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        pass

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    # Methods copied from AbstractUser
    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        return self.full_name

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    # Permissions methods, similar to those in PermissionsMixin
    def get_all_permissions(self, obj=None):
        permissions = set()
        for backend in auth.get_backends():
            permissions.update(backend.get_all_permissions(self, obj))
        return permissions

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        if perm == "wiki.moderate" and self.is_active and self.is_wiki_user:
            # There is some code in django-wiki that:
            # 1. checks for this permission
            #
            # 2. if it fails goes on to do a query that fails for us,
            #    due to the fact that we have 'Role' and not 'Group', and the
            #    different schema.
            #
            # So we avoid the bug by shortcutting here
            return True

        # Otherwise we need to check the backends.
        for backend in auth.get_backends():
            if not hasattr(backend, "has_perm"):
                continue
            try:
                if backend.has_perm(self, perm, obj):
                    return True
            except PermissionDenied:
                return False
        return False

    def has_perms(self, perm_list, obj=None):
        """
        Return True if the user has each of the specified permissions. If
        object is passed, check if the user has all required perms for it.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        """
        Return True if the user has any permissions in the given app label.
        Use similar logic as has_perm(), above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        for backend in auth.get_backends():
            if not hasattr(backend, "has_module_perms"):
                continue
            try:
                if backend.has_module_perms(self, app_label):
                    return True
            except PermissionDenied:
                return False
        return False

    # Login/password related

    def mark_password_validation_done(self):
        self.password_validators_used = _current_password_validators_as_string()

    def mark_password_validation_not_done(self):
        self.password_validators_used = ""

    def password_validation_needs_checking(self):
        return self.password_validators_used != _current_password_validators_as_string()

    def set_password(self, password):
        retval = super().set_password(password)
        # To avoid getting stuck on set password page,
        # we have to clear this flag
        self.clear_bad_password()
        return retval

    def mark_bad_password(self):
        self.bad_password = True
        self.mark_password_validation_done()

    def clear_bad_password(self):
        self.bad_password = False
        self.mark_password_validation_done()

    # Helpers for roles
    @cached_property
    def is_booking_secretary(user):
        if not active_staff(user):
            return False
        return user_has_role(user, [BOOKING_SECRETARY_ROLE_NAME])

    @cached_property
    def is_camp_admin(self):
        """
        Returns True if the user is an admin for any camp, or has rights
        for editing camp/officer/reference/DBS information
        """
        if not active_staff(self):
            return False
        return user_has_role(self, CAMP_MANAGER_ROLES) or len(self.current_camps_as_admin_or_leader) > 0

    @cached_property
    def is_potential_camp_officer(self):
        return active_staff(self)

    @cached_property
    def is_cciw_secretary(self):
        if not active_staff(self):
            return False
        return user_has_role(self, [SECRETARY_ROLE_NAME])

    @cached_property
    def is_committee_member(self):
        if not active_staff(self):
            return False
        return user_has_role(self, [COMMITTEE_ROLE_NAME])

    @cached_property
    def is_dbs_officer(self):
        if not active_staff(self):
            return False
        return user_has_role(self, [DBS_OFFICER_ROLE_NAME])

    @cached_property
    def is_wiki_user(self):
        if not active_staff(self):
            return False
        return user_has_role(self, WIKI_ROLES)

    @cached_property
    def can_manage_application_forms(self):
        if self.has_perm("officers.change_application"):
            return True
        if self.is_camp_admin:
            return True
        if self.is_dbs_officer:
            return True
        return False

    # These methods control permissions in admin
    def can_view_any_camps(self):
        if self.has_perm("cciwmain.view_camp"):
            return True
        # They only get view permissions for old camps when they also have
        # edit permissions for at least one camp. i.e. current leaders
        # can view old info, past leaders can't
        if self.viewable_camps and self.editable_camps:
            return True
        return False

    def can_view_camp(self, camp):
        # NB also viewable_camps
        if self.has_perm("cciwmain.view_camp"):
            return True

        if self.can_view_any_camps and camp in self.viewable_camps:
            return True
        return False

    @cached_property
    def viewable_camps(self):
        return self.camps_as_admin_or_leader

    @cached_property
    def can_edit_any_camps(self):
        if self.has_perm("cciwmain.change_camp"):
            return True
        if self.editable_camps:
            return True
        return False

    def can_edit_camp(self, camp):
        if self.has_perm("cciwmain.change_camp"):
            return True

        if self.can_edit_any_camps and camp in self.editable_camps:
            return True
        return False

    @cached_property
    def editable_camps(self):
        # We only allow current camps to be edited by
        # camp leaders, to avoid confusion and mistakes,
        # and avoid old leaders having access indefinitely
        return self.current_camps_as_admin_or_leader

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

        # re-use cached camps_as_admin_or_leader here.
        return [c for c in self.camps_as_admin_or_leader if c.year == common.get_thisyear()]

    @cached_property
    def can_search_officer_names(self):
        return self.is_dbs_officer or self.is_committee_member or self.is_cciw_secretary or self.is_camp_admin


class RoleQuerySet(models.QuerySet):
    def with_address(self):
        return self.exclude(email="")


class RoleManager(models.Manager.from_queryset(RoleQuerySet)):
    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Role(models.Model):
    """
    Roles are a generic way of categorizing users to apply permissions,
    and define email groups.
    """

    # This is similar to django.contrib.auth.models.Group,
    # with some changes:
    #
    # * We put the ManyToMany to User on the other side, because this gives us a
    #   nicer admin by default.
    #
    # * We don't have user level permissions - roles only.
    #
    # * We add things for managing email groups
    #
    # * See other notes in cciw.auth.backend
    name = models.CharField(max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )
    members = models.ManyToManyField(
        User,
        related_name="roles",
        help_text="This defines which users have access rights "
        "to all the functionality on the website related to this role. ",
    )

    # Email related
    email = models.EmailField(help_text="Email address including domain. Optional.", blank=True)
    email_recipients = models.ManyToManyField(
        User,
        related_name="roles_as_email_recipient",
        blank=True,
        help_text="This defines which users will be emailed for email sent to the role "
        'email address above. Usually the same as "members", or a subset, but could have '
        "additional people.",
    )
    allow_emails_from_public = models.BooleanField(
        default=False,
        help_text="If unchecked, the email address will be a group communication list, "
        "usable only by other members of the list.",
    )
    objects = RoleManager()

    class Meta:
        verbose_name_plural = "roles"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


def get_or_create_perm(app_label, model, codename):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    try:
        return Permission.objects.get(codename=codename, content_type=ct)
    except Permission.DoesNotExist:
        # This branch is generally only reached when running tests.
        return Permission.objects.create(codename=codename, name=codename, content_type=ct)


def setup_auth_roles():
    permissions_conf = yaml.load(open(settings.ROLES_CONFIG_FILE), Loader=yaml.SafeLoader)
    roles = permissions_conf["Roles"]
    for role_name, role_details in roles.items():
        role, _ = Role.objects.get_or_create(name=role_name)
        permission_details = role_details["Permissions"]
        perms = []
        for p in permission_details:
            app_and_model, perm = p.split("/")
            app_name, model = app_and_model.lower().split(".")
            perm = f"{perm}_{model}"
            perms.append(get_or_create_perm(app_name, model, perm))
        with transaction.atomic():
            role.permissions.set(perms)


def _current_password_validators_as_string():
    # Simple stringification that can handle AUTH_PASSWORD_VALIDATORS including
    # options. Applies canoninical ordering of dict keys for determinism.
    def val_to_str(val):
        if isinstance(val, dict):
            return "{" + ",".join(f"{k!r}:{val_to_str(v)}" for k, v in sorted(val.items())) + "}"
        elif isinstance(val, (str, int)):
            return repr(val)
        elif isinstance(val, list):
            return "[" + ",".join(f"{val_to_str(v)}" for v in val) + "]"
        else:
            raise AssertionError("Can't handle {type(val)}")

    return val_to_str(settings.AUTH_PASSWORD_VALIDATORS)


from . import hooks  # noqa
