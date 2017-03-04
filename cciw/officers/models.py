# -*- coding: utf-8 -*-
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils import timezone

from cciw.cciwmain.models import Camp
from cciw.officers.fields import (AddressField, ExplicitBooleanField, RequiredAddressField, RequiredCharField,
                                  RequiredDateField, RequiredEmailField, RequiredExplicitBooleanField,
                                  RequiredTextField, RequiredYyyyMmField, YyyyMmField)
from cciw.officers.references import first_letter_cap, reference_present_val

REFEREE_NUMBERS = [1, 2]

REFEREE_DATA_FIELDS = ['name', 'address', 'tel', 'mobile', 'email']


class ApplicationManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(ApplicationManager, self).get_queryset().select_related('officer')


NAME_LENGTH = 100
REFEREE_NAME_HELP_TEXT = "Name only - please do not include job title or other information."


class Application(models.Model):
    officer = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                blank=True,
                                related_name='applications')  # blank=True to get the admin to work
    full_name = RequiredCharField('full name', max_length=NAME_LENGTH)
    full_maiden_name = models.CharField('full maiden name', max_length=NAME_LENGTH, blank=True, help_text="Name before getting married.")
    birth_date = RequiredDateField('date of birth', null=True, default=None)
    birth_place = RequiredCharField('place of birth', max_length=60)
    address_firstline = RequiredCharField('address', max_length=40)
    address_town = RequiredCharField('town/city', max_length=60)  # 60 == len("Llanfairpwllgwyngyllgogerychwyrndrobwyll-llantysiliogogogoch")
    address_county = RequiredCharField('county', max_length=30)
    address_postcode = RequiredCharField('post code', max_length=10)
    address_country = RequiredCharField('country', max_length=30)
    address_tel = RequiredCharField('telephone', max_length=22, blank=True)  # +44-(0)1224-XXXX-XXXX
    address_mobile = models.CharField('mobile', max_length=22, blank=True)
    address_email = RequiredEmailField('email')
    address_since = RequiredYyyyMmField('resident at address since')

    address2_from = YyyyMmField('resident at address from', blank=True)
    address2_to = YyyyMmField('resident at address until', blank=True)
    address2_address = AddressField('address', blank=True)

    address3_from = YyyyMmField('resident at address from', blank=True)
    address3_to = YyyyMmField('resident at address until', blank=True)
    address3_address = AddressField('address', blank=True)

    christian_experience = RequiredTextField('christian experience')
    youth_experience = RequiredTextField('youth work experience')

    youth_work_declined = RequiredExplicitBooleanField('Have you ever had an offer to work with children/young people declined?')
    youth_work_declined_details = models.TextField('details', blank=True)

    relevant_illness = RequiredExplicitBooleanField('''Do you suffer or have you suffered from any
            illness which may directly affect your work with children/young people?''')
    illness_details = models.TextField('illness details', blank=True)

    employer1_name = models.CharField("1. Employer's name and address", max_length=NAME_LENGTH, blank=True)
    employer1_from = YyyyMmField("Employed from", blank=True)
    employer1_to = YyyyMmField("Employed until", blank=True)
    employer1_job = models.CharField("Job description", max_length=60, blank=True)
    employer1_leaving = models.CharField("Reason for leaving", max_length=150, blank=True)

    employer2_name = models.CharField("2. Employer's name and address", max_length=NAME_LENGTH, blank=True)
    employer2_from = YyyyMmField("Employed from", blank=True)
    employer2_to = YyyyMmField("Employed until", blank=True)
    employer2_job = models.CharField("Job description", max_length=60, blank=True)
    employer2_leaving = models.CharField("Reason for leaving", max_length=150, blank=True)

    crime_declaration = RequiredExplicitBooleanField(
        """Have you ever been charged with or convicted """
        """of a criminal offence or are the subject of criminal """
        """proceedings?""")
    crime_details = models.TextField("If yes, give details", blank=True)

    court_declaration = RequiredExplicitBooleanField(
        '''Have you ever been involved in Court
           proceedings concerning a child for whom you have
           parental responsibility?''')
    court_details = models.TextField("If yes, give details", blank=True)

    concern_declaration = RequiredExplicitBooleanField(
        """Has there ever been any cause for concern """
        """regarding your conduct with children/young people?""")
    concern_details = models.TextField("If yes, give details", blank=True)

    allegation_declaration = RequiredExplicitBooleanField(
        """To your knowledge have you ever had any """
        """allegation made against you concerning children/young people """
        """which has been reported to and investigated by Social """
        """Services and /or the Police?""")

    dbs_number = models.CharField("DBS number",
                                  max_length=128, default="", blank=True,
                                  help_text="Current enhanced DBS number with update service")
    dbs_check_consent = ExplicitBooleanField(
        """Do you consent to the obtaining of a Disclosure and Barring """
        """Service check on yourself? """)

    finished = models.BooleanField("is the above information complete?", default=False)

    date_submitted = models.DateField('date submitted', null=True, blank=True)

    objects = ApplicationManager()

    @property
    def referees(self):
        """A cached version of 2 items that can exist in 'references_set', which
        are created if they don't exist. Read only"""
        try:
            return self._referees_cache
        except AttributeError:
            retval = (self._referee(1), self._referee(2))
            self._referees_cache = retval
            return retval

    @property
    def one_line_address(self):
        return ", ".join(filter(bool, [self.address_firstline,
                                       self.address_town,
                                       self.address_county,
                                       self.address_postcode,
                                       self.address_country]))

    def __str__(self):
        if self.date_submitted is not None:
            submitted = "submitted " + self.date_submitted.strftime("%Y-%m-%d")
        else:
            submitted = "incomplete"
        return "Application from %s (%s)" % (self.full_name, submitted)

    def _referee(self, num):
        if hasattr(self, '_prefetched_objects_cache'):
            if 'referee' in self._prefetched_objects_cache:
                vals = [v for v in self._prefetched_objects_cache['referee']
                        if v.referee_number == num]
                if len(vals) == 1:
                    return vals[0]
        return self.referee_set.get_or_create(referee_number=num)[0]

    class Meta:
        ordering = ('-date_submitted', 'officer__first_name', 'officer__last_name',)

    def could_be_for_camp(self, camp):
        # An application is 'for' a camp if it is submitted in the year before
        # the camp start date. Logic duplicated in applications_for_camp
        return (self.date_submitted <= camp.start_date and
                self.date_submitted > camp.start_date - timedelta(days=365))

    def clean(self):
        super(Application, self).clean()
        if self.finished:
            if self.dbs_number.strip() == "" and self.dbs_check_consent is None:
                raise ValidationError({'dbs_check_consent':
                                       "If you do not provide a DBS number, you "
                                       "must answer this question."})


class Referee(models.Model):
    # Referee applies to one Application only, and has to be soft-matched to
    # subsequent Applications by the same officer, even if the referee is the
    # same, because the officer could put different things in for their name.

    # This model also acts as an anchor for everything related to requesting
    # the reference from this referee.

    application = models.ForeignKey(Application,
                                    on_delete=models.CASCADE,
                                    limit_choices_to={'finished': True})
    referee_number = models.SmallIntegerField("Referee number", choices=[(n, str(n)) for n in REFEREE_NUMBERS])

    name = RequiredCharField("Name", max_length=NAME_LENGTH,
                             help_text=REFEREE_NAME_HELP_TEXT)
    address = RequiredAddressField('address')
    tel = models.CharField('telephone', max_length=22, blank=True)  # +44-(0)1224-XXXX-XXXX
    mobile = models.CharField('mobile', max_length=22, blank=True)
    email = models.EmailField('email', blank=True)

    def __str__(self):
        return "{0} for {1}".format(self.name, self.application.officer.username)

    log_datetime_format = "%Y-%m-%d %H:%M:%S"

    def reference_is_received(self):
        try:
            return not empty_reference(self.reference)
        except Reference.DoesNotExist:
            return False

    def reference_was_requested(self):
        return self.last_requested is not None

    @property
    def last_requested(self):
        """
        Returns the last date the reference was requested,
        or None if it is not known.
        """
        if hasattr(self, '_prefetched_objects_cache'):
            if 'actions' in self._prefetched_objects_cache:
                actions = [a for a in self._prefetched_objects_cache['actions']
                           if a.action_type == ReferenceAction.REFERENCE_REQUESTED]
                if actions:
                    last = sorted(actions, key=lambda a: a.created)[-1]
                else:
                    last = None
        else:
            last = self.actions.filter(action_type=ReferenceAction.REFERENCE_REQUESTED).order_by('created').last()
        if last:
            return last.created
        else:
            return None

    def log_reference_received(self, dt):
        self.actions.create(action_type=ReferenceAction.REFERENCE_RECEIVED,
                            created=dt)

    def log_reference_filled_in(self, user, dt):
        self.actions.create(action_type=ReferenceAction.REFERENCE_FILLED_IN,
                            created=dt,
                            user=user)

    def log_request_made(self, user, dt):
        self.actions.create(action_type=ReferenceAction.REFERENCE_REQUESTED,
                            created=dt,
                            user=user)

    def log_nag_made(self, user, dt):
        self.actions.create(action_type=ReferenceAction.REFERENCE_NAG,
                            created=dt,
                            user=user)

    class Meta:
        ordering = ('application__date_submitted',
                    'application__officer__first_name',
                    'application__officer__last_name',
                    'referee_number')
        unique_together = (("application", "referee_number"),)


class ReferenceAction(models.Model):
    REFERENCE_REQUESTED = "requested"
    REFERENCE_RECEIVED = "received"
    REFERENCE_FILLED_IN = "filledin"
    REFERENCE_NAG = "nag"

    ACTION_CHOICES = [
        (REFERENCE_REQUESTED, "Reference requested"),
        (REFERENCE_RECEIVED, "Reference received"),
        (REFERENCE_FILLED_IN, "Reference filled in manually"),
        (REFERENCE_NAG, "Applicant nagged"),
    ]
    referee = models.ForeignKey(Referee,
                                on_delete=models.CASCADE,
                                related_name="actions")
    created = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             null=True)

    # This is set to True only for some records which had to be partially
    # invented in a database migration due to missing data. Any stats on this
    # table should exclude these records.
    inaccurate = models.BooleanField(default=False)

    class Meta:
        ordering = [('created')]

    def __repr__(self):
        return "<ReferenceAction {0} {1} | {2}>".format(self.action_type, self.created, self.referee)


def empty_reference(reference):
    return reference is None or reference.how_long_known.strip() == ""


class ReferenceManager(models.Manager):
    # manager to reduce number of SQL queries, especially in admin
    use_for_related_fields = True

    def get_queryset(self):
        return super(ReferenceManager, self).get_queryset().select_related('referee__application__officer')


class Reference(models.Model):
    referee_name = models.CharField("name of referee", max_length=NAME_LENGTH,
                                    help_text=REFEREE_NAME_HELP_TEXT)
    how_long_known = models.CharField("how long/since when have you known the applicant?", max_length=150)
    capacity_known = models.TextField("in what capacity do you know the applicant?")
    known_offences = models.BooleanField("""The position for which the applicant is applying requires substantial contact with children and young people. To the best of your knowledge, does the applicant have any convictions/cautions/bindovers, for any criminal offences?""", blank=True, default=False)
    known_offences_details = models.TextField("If the answer is yes, please identify", blank=True)
    capability_children = models.TextField("Please comment on the applicant's capability of working with children and young people (ie. previous experience of similar work, sense of responsibility, sensitivity, ability to work with others, ability to communicate with children and young people, leadership skills)")
    character = models.TextField("Please comment on aspects of the applicants character (ie. Christian experience honesty, trustworthiness, reliability, disposition, faithful attendance at worship/prayer meetings.)")
    concerns = models.TextField("Have you ever had concerns about either this applicant's ability or suitability to work with children and young people?")
    comments = models.TextField("Any other comments you wish to make", blank=True)
    date_created = models.DateField("date created")
    referee = models.OneToOneField(Referee,
                                   on_delete=models.CASCADE)

    # This is set to True only for some records which had to be partially
    # invented in a database migration due to missing data. Any stats on this
    # table should exclude these records.
    inaccurate = models.BooleanField(default=False)

    objects = ReferenceManager()

    @property
    def applicant_name(self):
        o = self.referee.application.officer
        return "%s %s" % (o.first_name, o.last_name)

    def __str__(self):
        officer = self.referee.application.officer
        return "Reference form for %s %s by %s" % (officer.first_name, officer.last_name, self.referee_name)

    def save(self, *args, **kwargs):
        retval = super(Reference, self).save(*args, **kwargs)
        # Update application form data with name of referee
        referee = self.referee
        referee.name = self.referee_name
        referee.save()
        return retval

    class Meta:
        verbose_name = "Reference"

    def reference_display_fields(self):
        """
        Name/value pairs for all user presentable
        information in Reference
        """
        # Avoid hard coding strings into templates by using field verbose_name from model
        return [(first_letter_cap(f.verbose_name), reference_present_val(getattr(self, f.attname)))
                for f in self._meta.fields if f.attname not in ['id', 'referee_id', 'inaccurate']]


class QualificationType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Qualification(models.Model):
    application = models.ForeignKey(Application, related_name='qualifications')
    type = models.ForeignKey(QualificationType, related_name='qualifications')
    date_issued = models.DateField()

    def __str__(self):
        return "{0} qualification for {1}".format(self.type, self.application.officer)

    def copy(self, **kwargs):
        q = Qualification()
        q.application = self.application
        q.type = self.type
        q.date_issued = self.date_issued
        for k, v in kwargs.items():
            setattr(q, k, v)
        return q

    class Meta:
        ordering = ['application', 'type__name']
        unique_together = [
            ('application', 'type')
        ]


class InvitationManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(InvitationManager, self).get_queryset().select_related('officer', 'camp', 'camp__chaplain')


class Invitation(models.Model):
    officer = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='invitations')
    camp = models.ForeignKey(Camp,
                             on_delete=models.CASCADE,
                             related_name='invitations')
    date_added = models.DateField(default=date.today)
    notes = models.CharField(max_length=255, blank=True)

    objects = InvitationManager()

    def __str__(self):
        return "%s %s — camp %s" % (self.officer.first_name, self.officer.last_name, self.camp)

    class Meta:
        ordering = ('-camp__year', 'officer__first_name', 'officer__last_name')
        unique_together = (('officer', 'camp'),)


# CRBs/DBSs - Criminal Records Bureau/Disclosure and Barring Service
#
# Related models and fields in the past were named 'CRB', and now renamed to
# 'DBS' for consistency with new DBS features. Older data was technically a CRB
# not DBS.

class DBSCheckManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(DBSCheckManager, self).get_queryset().select_related('officer')

    def get_for_camp(self, camp, include_late=False):
        """
        Returns the DBSs that might be valid for a camp (ignoring the camp
        officer list)
        """
        # This logic is duplicated in cciw.officers.views.stats.

        # We include DBS applications that are after the camp date, for the sake
        # of the 'manage_dbss' function which might be used even after the camp
        # has run.
        qs = self.get_queryset().filter(completed__gte=camp.start_date - timedelta(settings.DBS_VALID_FOR))
        if not include_late:
            qs = qs.filter(completed__lte=camp.start_date)
        return qs


class DBSCheck(models.Model):
    REQUESTED_BY_CCIW = 'CCIW'
    REQUESTED_BY_OTHER = 'other'
    REQUESTED_BY_UKNOWN = 'unknown'
    REQUESTED_BY_CHOICES = [
        (REQUESTED_BY_CCIW, 'CCIW'),
        (REQUESTED_BY_OTHER, 'Other organisation'),
        (REQUESTED_BY_UKNOWN, 'Unknown'),
    ]

    CHECK_TYPE_FORM = 'form'
    CHECK_TYPE_ONLINE = 'online'
    CHECK_TYPE_CHOICES = [
        (CHECK_TYPE_FORM, 'Full form'),
        (CHECK_TYPE_ONLINE, 'Online check'),
    ]

    officer = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='dbs_checks')
    dbs_number = models.CharField("Disclosure number", max_length=20)
    check_type = models.CharField("check type", max_length=20,
                                  choices=CHECK_TYPE_CHOICES,
                                  default=CHECK_TYPE_FORM)
    completed = models.DateField("Date of issue/check",
                                 help_text="For full forms, use the date of issue. For online checks, use the date of the check")
    requested_by = models.CharField(max_length=20, choices=REQUESTED_BY_CHOICES, default=REQUESTED_BY_UKNOWN)
    other_organisation = models.CharField(max_length=255, blank=True)
    registered_with_dbs_update = models.NullBooleanField("registered with DBS update service")

    objects = DBSCheckManager()

    def __str__(self):
        return "DBS check for %s %s, %s" % (self.officer.first_name,
                                            self.officer.last_name,
                                            self.completed.strftime("%Y-%m-%d"))

    class Meta:
        verbose_name = "DBS/CRB check"
        verbose_name_plural = "DBS/CRB check"

    def could_be_for_camp(self, camp):
        return (self.completed >= camp.start_date - timedelta(days=settings.DBS_VALID_FOR) and
                self.completed <= camp.start_date)


class DBSActionLogManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(DBSActionLogManager, self).get_queryset().select_related('officer')

    def create(self, *args, **kwargs):
        if 'action_type' not in kwargs:
            raise TypeError("action_type is a required field")
        super(DBSActionLogManager, self).create(*args, **kwargs)


class DBSActionLog(models.Model):
    """
    Represents a log of a DBS form sent to an officer
    """
    ACTION_FORM_SENT = 'form_sent'
    ACTION_LEADER_ALERT_SENT = 'leader_alert_sent'
    ACTION_CHOICES = [
        (ACTION_FORM_SENT, "DBS form sent"),
        (ACTION_LEADER_ALERT_SENT, "Alert sent to leader"),
    ]

    officer = models.ForeignKey(settings.AUTH_USER_MODEL,
                                related_name='dbsactionlogs',
                                on_delete=models.CASCADE)
    action_type = models.CharField("action type", max_length=20,
                                   choices=ACTION_CHOICES)
    timestamp = models.DateTimeField("Timestamp",
                                     default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name="User who performed action",
                             related_name='dbsactions_performed',
                             null=True, blank=True,
                             default=None,
                             on_delete=models.SET_NULL)

    objects = DBSActionLogManager()

    def __str__(self):
        return "Log of DBS form sent to %s %s on %s" % (self.officer.first_name,
                                                        self.officer.last_name,
                                                        self.timestamp.strftime("%Y-%m-%d"))

    class Meta:
        verbose_name = "DBS action log"
        verbose_name_plural = "DBS action logs"


# This is monkey patched on User in apps.py as a cached property, so it is best
# used as user.camps_as_admin_or_leader.
def camps_as_admin_or_leader(user):
    """
    Returns all the camps for which the user is an admin or leader.
    """
    # If the user is am 'admin' for some camps:
    camps = user.camps_as_admin.all()
    # Find the 'Person' objects that correspond to this user
    leaders = list(user.people.all())
    # Find the camps for this leader
    # (We could do:
    #    Person.objects.get(user=user.id).camps_as_leader.all(),
    #  but we also must we handle the possibility that two Person
    #  objects have the same User objects, which could happen in the
    #  case where a leader leads by themselves and as part of a couple)
    for leader in leaders:
        camps = camps | leader.camps_as_leader.all()

    return camps.distinct()
