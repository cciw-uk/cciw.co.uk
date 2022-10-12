from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from cciw.cciwmain.models import Camp
from cciw.officers.fields import (
    RequiredAddressField,
    RequiredCharField,
    RequiredDateField,
    RequiredEmailField,
    RequiredExplicitBooleanField,
    RequiredTextField,
)
from cciw.officers.references import first_letter_cap, reference_present_val
from cciw.utils.models import ClearCachedPropertyMixin

REFEREE_NUMBERS = [1, 2]

REFEREE_DATA_FIELDS = ["name", "capacity_known", "address", "tel", "mobile", "email"]


class ApplicationQuerySet(models.QuerySet):
    def older_than(self, before_datetime):
        return self.filter(date_saved__lt=before_datetime.date())


class ApplicationManagerBase(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("officer")


ApplicationManager = ApplicationManagerBase.from_queryset(ApplicationQuerySet)


NAME_LENGTH = 100
REFEREE_NAME_HELP_TEXT = "Name only - please do not include job title or other information."


class Application(ClearCachedPropertyMixin, models.Model):
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, related_name="applications"
    )  # blank=True to get the admin to work
    full_name = RequiredCharField("full name", max_length=NAME_LENGTH)
    birth_date = RequiredDateField("date of birth", null=True, default=None)
    birth_place = RequiredCharField("place of birth", max_length=60)
    address_firstline = RequiredCharField("address", max_length=40)
    address_town = RequiredCharField(
        "town/city", max_length=60
    )  # 60 == len("Llanfairpwllgwyngyllgogerychwyrndrobwyll-llantysiliogogogoch")
    address_county = RequiredCharField("county", max_length=30)
    address_postcode = RequiredCharField("post code", max_length=10)
    address_country = RequiredCharField("country", max_length=30)
    address_tel = RequiredCharField("telephone", max_length=22, blank=True)  # +44-(0)1224-XXXX-XXXX
    address_mobile = models.CharField("mobile", max_length=22, blank=True)
    address_email = RequiredEmailField("email")

    christian_experience = RequiredTextField("christian experience")
    youth_experience = RequiredTextField("youth work experience")

    youth_work_declined = RequiredExplicitBooleanField(
        "Have you ever had an offer to work with children/young people declined?"
    )
    youth_work_declined_details = models.TextField("details", blank=True)

    relevant_illness = RequiredExplicitBooleanField(
        """Do you suffer or have you suffered from any
            illness which may directly affect your work with children/young people?"""
    )
    illness_details = models.TextField("illness details", blank=True)
    dietary_requirements = models.TextField("dietary requirements (if any)", blank=True)

    crime_declaration = RequiredExplicitBooleanField(
        """Have you ever been charged with or convicted """
        """of a criminal offence or are the subject of criminal """
        """proceedings?"""
    )
    crime_details = models.TextField("If yes, give details", blank=True)

    court_declaration = RequiredExplicitBooleanField(
        """Have you ever been involved in Court
           proceedings concerning a child for whom you have
           parental responsibility?"""
    )
    court_details = models.TextField("If yes, give details", blank=True)

    concern_declaration = RequiredExplicitBooleanField(
        """Has there ever been any cause for concern """ """regarding your conduct with children/young people?"""
    )
    concern_details = models.TextField("If yes, give details", blank=True)

    allegation_declaration = RequiredExplicitBooleanField(
        """To your knowledge have you ever had any """
        """allegation made against you concerning children/young people """
        """which has been reported to and investigated by Social """
        """Services and /or the Police?"""
    )

    dbs_number = models.CharField(
        "DBS number",
        max_length=128,
        default="",
        blank=True,
        help_text="Current enhanced DBS number with update service. Number usually starts 00…",
    )
    dbs_check_consent = RequiredExplicitBooleanField(
        """Do you consent to the obtaining of a Disclosure and Barring """ """Service check on yourself? """
    )

    finished = models.BooleanField("is the above information complete?", default=False)

    # Date the information was saved - not updated after 'finished' is set to
    # True.
    date_saved = models.DateField("date saved", null=True, blank=True)

    erased_on = models.DateTimeField(null=True, blank=True, default=None)

    objects = ApplicationManager()

    class Meta:
        ordering = (
            "-date_saved",
            "officer__first_name",
            "officer__last_name",
        )
        base_manager_name = "objects"

    @cached_property
    def referees(self):
        """A cached version of 2 items that can exist in 'references_set', which
        are created if they don't exist. Read only"""
        return (self._referee(1), self._referee(2))

    @property
    def one_line_address(self):
        return ", ".join(
            filter(
                bool,
                [
                    self.address_firstline,
                    self.address_town,
                    self.address_county,
                    self.address_postcode,
                    self.address_country,
                ],
            )
        )

    def __str__(self):
        if self.date_saved is not None:
            submitted = ("submitted " if self.finished else "saved ") + self.date_saved.strftime("%Y-%m-%d")
        else:
            submitted = "incomplete"
        return f"Application from {self.full_name} ({submitted})"

    def _referee(self, num):
        if hasattr(self, "_prefetched_objects_cache"):
            if "referee" in self._prefetched_objects_cache:
                vals = [v for v in self._prefetched_objects_cache["referee"] if v.referee_number == num]
                if len(vals) == 1:
                    return vals[0]
        return self.referee_set.get_or_create(referee_number=num)[0]

    def could_be_for_camp(self, camp):
        # An application is 'for' a camp if it is submitted in the year before
        # the camp start date. Logic duplicated in applications_for_camp
        return self.date_saved <= camp.start_date and self.date_saved > camp.start_date - timedelta(days=365)

    def clear_out_old_unfinished(self):
        # This is called when an application is created and saved by the
        # officer. In some cases it could be when a leader is editing old
        # application form of their own, in which case we don't want to delete a
        # currently in progress more recent application form.

        others = self.officer.applications.exclude(id=self.id)
        unfinished = others.filter(finished=False)
        unsaved = unfinished.filter(date_saved__isnull=True)

        # We can definitely delete all other old unsaved applications:
        to_delete = unsaved

        # We can also delete any unfinished application forms with
        # a date_saved before this one:
        if self.date_saved is not None:
            unfinshed_saved_earlier = unfinished.filter(date_saved__lt=self.date_saved)
            to_delete = to_delete | unfinshed_saved_earlier
        to_delete.delete()


class Referee(models.Model):
    # Referee applies to one Application only, and has to be soft-matched to
    # subsequent Applications by the same officer, even if the referee is the
    # same, because the officer could put different things in for their name.

    # This model also acts as an anchor for everything related to requesting
    # the reference from this referee.

    application = models.ForeignKey(Application, on_delete=models.CASCADE, limit_choices_to={"finished": True})
    referee_number = models.SmallIntegerField("Referee number", choices=[(n, str(n)) for n in REFEREE_NUMBERS])

    name = RequiredCharField("Name", max_length=NAME_LENGTH, help_text=REFEREE_NAME_HELP_TEXT)
    capacity_known = RequiredCharField(
        "Capacity known", max_length=255, help_text="In what capacity does the referee know you? (see above)"
    )
    address = RequiredAddressField("address")
    tel = models.CharField("telephone", max_length=22, blank=True)  # +44-(0)1224-XXXX-XXXX
    mobile = models.CharField("mobile", max_length=22, blank=True)
    email = models.EmailField("email", blank=True)

    def __str__(self):
        return f"{self.name} for {self.application.officer.username}"

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
        if hasattr(self, "_prefetched_objects_cache"):
            if "actions" in self._prefetched_objects_cache:
                actions = [
                    a
                    for a in self._prefetched_objects_cache["actions"]
                    if a.action_type == ReferenceAction.ActionType.REQUESTED
                ]
                if actions:
                    last = sorted(actions, key=lambda a: a.created_at)[-1]
                else:
                    last = None
        else:
            last = self.actions.filter(action_type=ReferenceAction.ActionType.REQUESTED).order_by("created_at").last()
        if last:
            return last.created_at
        else:
            return None

    def log_reference_received(self, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.RECEIVED, created_at=dt)

    def log_reference_filled_in(self, user, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.FILLED_IN, created_at=dt, user=user)

    def log_request_made(self, user, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.REQUESTED, created_at=dt, user=user)

    def log_nag_made(self, user, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.NAG, created_at=dt, user=user)

    class Meta:
        ordering = (
            "application__date_saved",
            "application__officer__first_name",
            "application__officer__last_name",
            "referee_number",
        )
        unique_together = (("application", "referee_number"),)


class ReferenceAction(models.Model):
    class ActionType(models.TextChoices):
        REQUESTED = "requested", "Reference requested"
        RECEIVED = "received", "Reference received"
        FILLED_IN = "filledin", "Reference filled in manually"
        NAG = "nag", "Applicant nagged"

    referee = models.ForeignKey(Referee, on_delete=models.CASCADE, related_name="actions")
    created_at = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)

    # This is set to True only for some records which had to be partially
    # invented in a database migration due to missing data. Any stats on this
    # table should exclude these records.
    inaccurate = models.BooleanField(default=False)

    class Meta:
        ordering = [("created_at")]

    def __repr__(self):
        return f"<ReferenceAction {self.action_type} {self.created_at} | {self.referee}>"


def empty_reference(reference):
    return reference is None or reference.how_long_known.strip() == ""


class ReferenceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("referee__application__officer")


class Reference(models.Model):
    referee_name = models.CharField("name of referee", max_length=NAME_LENGTH, help_text=REFEREE_NAME_HELP_TEXT)
    how_long_known = models.CharField("how long/since when have you known the applicant?", max_length=150)
    capacity_known = models.TextField("in what capacity do you know the applicant?")
    known_offences = models.BooleanField(
        """The position for which the applicant is applying requires substantial contact with children and young people. To the best of your knowledge, does the applicant have any convictions/cautions/bindovers, for any criminal offences?""",
        blank=True,
        default=False,
    )
    known_offences_details = models.TextField("If the answer is yes, please identify", blank=True)
    capability_children = models.TextField(
        "Please comment on the applicant's capability of working with children and young people (ie. previous experience of similar work, sense of responsibility, sensitivity, ability to work with others, ability to communicate with children and young people, leadership skills)"
    )
    character = models.TextField(
        "Please comment on aspects of the applicants character (ie. Christian experience honesty, trustworthiness, reliability, disposition, faithful attendance at worship/prayer meetings.)"
    )
    concerns = models.TextField(
        "Have you ever had concerns about either this applicant's ability or suitability to work with children and young people?"
    )
    comments = models.TextField("Any other comments you wish to make", blank=True)
    given_in_confidence = models.BooleanField(
        help_text="""Is this reference given "in confidence"? If yes, in the case that the applicant wishes to see the contents of the references made about them under a GDPR "Right of access" request, we will exclude the contents of this reference. It is important to us that you feel at liberty to tell us any concerns you have about the applicant, so you may tick this box if you feel it is necessary.""",
        default=False,
    )
    date_created = models.DateField("date created")
    referee = models.OneToOneField(Referee, on_delete=models.CASCADE)

    # This is set to True only for some records which had to be partially
    # invented in a database migration due to missing data. Any stats on this
    # table should exclude these records.
    inaccurate = models.BooleanField(default=False)

    objects = ReferenceManager()

    class Meta:
        base_manager_name = "objects"
        verbose_name = "reference"

    @property
    def applicant_name(self):
        return self.referee.application.officer.full_name

    def __str__(self):
        officer = self.referee.application.officer
        return f"Reference form for {officer.full_name} by {self.referee_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update application form data with name of referee
        referee = self.referee
        referee.name = self.referee_name
        referee.save()

    def reference_display_fields(self):
        """
        Name/value pairs for all user presentable
        information in Reference
        """
        # Avoid hard coding strings into templates by using field verbose_name from model
        return [
            (first_letter_cap(f.verbose_name), reference_present_val(getattr(self, f.attname)))
            for f in self._meta.fields
            if f.attname not in ["id", "referee_id", "inaccurate"]
        ]


class QualificationType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Qualification(models.Model):
    application = models.ForeignKey(Application, related_name="qualifications", on_delete=models.CASCADE)
    type = models.ForeignKey(QualificationType, related_name="qualifications", on_delete=models.PROTECT)
    date_issued = models.DateField()

    def __str__(self):
        return f"{self.type} qualification for {self.application.officer}"

    def copy(self, **kwargs):
        q = Qualification()
        q.application = self.application
        q.type = self.type
        q.date_issued = self.date_issued
        for k, v in kwargs.items():
            setattr(q, k, v)
        return q

    class Meta:
        ordering = ["application", "type__name"]
        unique_together = [("application", "type")]


class InvitationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("officer", "camp", "camp__chaplain")


class Invitation(models.Model):
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invitations")
    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="invitations")
    date_added = models.DateField(default=date.today)
    notes = models.CharField(max_length=255, blank=True)

    objects = InvitationManager()

    class Meta:
        ordering = ("-camp__year", "officer__first_name", "officer__last_name")
        unique_together = (("officer", "camp"),)
        base_manager_name = "objects"

    def __str__(self):
        return f"{self.officer.full_name} — camp {self.camp}"


# CRBs/DBSs - Criminal Records Bureau/Disclosure and Barring Service
#
# Related models and fields in the past were named 'CRB', and now renamed to
# 'DBS' for consistency with new DBS features. Older data was technically a CRB
# not DBS.


class DBSCheckManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("officer")

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
    class RequestedBy(models.TextChoices):
        CCIW = "CCIW", "CCiW"
        OTHER = "other", "Other organisation"
        UNKNOWN = "unknown", "Unknown"

    class CheckType(models.TextChoices):
        FORM = "form", "Full form"
        ONLINE = "online", "Online check"

    officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dbs_checks")
    dbs_number = models.CharField("Disclosure number", max_length=20)
    check_type = models.CharField("check type", max_length=20, choices=CheckType.choices, default=CheckType.FORM)
    completed = models.DateField(
        "Date of issue/check",
        help_text="For full forms, use the date of issue. For online checks, use the date of the check",
    )
    requested_by = models.CharField(
        max_length=20,
        choices=RequestedBy.choices,
        default=RequestedBy.UNKNOWN,
        help_text="The organisation that asked for this DBS to be done, " "normally CCiW.",
    )
    other_organisation = models.CharField(
        max_length=255, blank=True, help_text="If previous answer is not CCiW, please fill in"
    )
    applicant_accepted = models.BooleanField(
        default=True, help_text="Uncheck if the applicant could not be accepted " "on the basis of this DBS check"
    )

    registered_with_dbs_update = models.BooleanField("registered with DBS update service", null=True)

    objects = DBSCheckManager()

    def __str__(self):
        return f"DBS check for {self.officer.full_name}, {self.completed:%Y-%m-%d}"

    class Meta:
        verbose_name = "DBS/CRB check"
        verbose_name_plural = "DBS/CRB check"
        base_manager_name = "objects"

    def could_be_for_camp(self, camp):
        return (
            self.completed >= camp.start_date - timedelta(days=settings.DBS_VALID_FOR)
            and self.completed <= camp.start_date
        )


class DBSActionLogManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("officer")

    def create(self, *args, **kwargs):
        if "action_type" not in kwargs:
            raise TypeError("action_type is a required field")
        return super().create(*args, **kwargs)


class DBSActionLog(models.Model):
    """
    Represents a log of a DBS action done by DBS officer
    """

    ACTION_FORM_SENT = "form_sent"
    ACTION_LEADER_ALERT_SENT = "leader_alert_sent"
    ACTION_REQUEST_FOR_DBS_FORM_SENT = "request_for_dbs_form_sent"
    ACTION_CHOICES = [
        (ACTION_FORM_SENT, "DBS form sent"),
        (ACTION_LEADER_ALERT_SENT, "Alert sent to leader"),
        (ACTION_REQUEST_FOR_DBS_FORM_SENT, "Request for DBS form sent"),
    ]

    officer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="dbsactionlogs", on_delete=models.PROTECT)
    action_type = models.CharField("action type", max_length=40, choices=ACTION_CHOICES)
    created_at = models.DateTimeField("Created at", default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="User who performed action",
        related_name="dbsactions_performed",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    objects = DBSActionLogManager()

    class Meta:
        base_manager_name = "objects"
        verbose_name = "DBS action log"
        verbose_name_plural = "DBS action logs"

    def __str__(self):
        return f"Log of DBS action '{self.get_action_type_display()}' for {self.officer.full_name}, {self.created_at:%Y-%m-%d}"
