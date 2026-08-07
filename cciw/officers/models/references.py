from __future__ import annotations

from datetime import datetime, timedelta

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Value
from django.db.models.functions import Concat
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.functional import cached_property

from cciw.accounts.models import User
from cciw.officers.fields import (
    RequiredAddressField,
    RequiredCharField,
)
from cciw.officers.references import first_letter_cap, reference_present_val

from .applications import Application
from .common import NAME_LENGTH

TITLES = ["dr", "rev", "reverend", "pastor", "mr", "ms", "mrs", "prof"]


REFEREE_NUMBERS = [1, 2]

REFEREE_DATA_FIELDS = ["name", "capacity_known", "address", "tel", "mobile", "email"]
REFEREE_DATA_FIELDS_TO_COPY_FROM_PREVIOUS = REFEREE_DATA_FIELDS
REFEREE_NAME_HELP_TEXT = "Name only - please do not include job title or other information."


def no_titles(name: str) -> None:
    if name.lower().split(" ")[0] in TITLES:
        raise ValidationError("Do not include title in name.")


def normalized_name(name: str) -> str:
    # See also application_form.js
    first_word = name.strip().split(" ")[0].lower().replace(".", "")
    if first_word in TITLES:
        name = name[len(first_word) :].strip(".").strip()
    return name


class Referee(models.Model):
    # Referee applies to one Application only, and has to be soft-matched to
    # subsequent Applications by the same officer, even if the referee is the
    # same, because the officer could put different things in for their name.

    # This model also acts as an anchor for everything related to requesting
    # the reference from this referee.

    application = models.ForeignKey(Application, on_delete=models.CASCADE, limit_choices_to={"finished": True})
    referee_number = models.SmallIntegerField("Referee number", choices=[(n, str(n)) for n in REFEREE_NUMBERS])

    name = RequiredCharField("Name", max_length=NAME_LENGTH, help_text=REFEREE_NAME_HELP_TEXT, validators=[no_titles])
    capacity_known = RequiredCharField(
        "Capacity known", max_length=255, help_text="In what capacity does the referee know you? (see above)"
    )
    address = RequiredAddressField("address")
    tel = models.CharField("telephone", max_length=30, blank=True)  # +44-(0)1224-XXXX-XXXX
    mobile = models.CharField("mobile", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)

    def __str__(self):
        return f"{self.name} for {self.application.officer.username}"

    log_datetime_format = "%Y-%m-%d %H:%M:%S"

    def reference_is_received(self) -> bool:
        try:
            return not empty_reference(self.reference)
        except Reference.DoesNotExist:
            return False

    def reference_was_requested(self) -> bool:
        return self.last_requested is not None

    @cached_property
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

    def log_reference_received(self, dt: datetime):
        self.actions.create(action_type=ReferenceAction.ActionType.RECEIVED, created_at=dt)

    def log_reference_filled_in(self, user, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.FILLED_IN, created_at=dt, user=user)

    def log_request_made(self, user: User, dt: datetime):
        self.actions.create(action_type=ReferenceAction.ActionType.REQUESTED, created_at=dt, user=user)

    def log_nag_made(self, user, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.NAG, created_at=dt, user=user)

    def log_details_corrected(self, user, dt):
        self.actions.create(action_type=ReferenceAction.ActionType.DETAILS_CORRECTED, created_at=dt, user=user)

    def log_email_bounced(self, dt: datetime, *, bounced_email: str):
        self.actions.create(
            action_type=ReferenceAction.ActionType.EMAIL_TO_REFEREE_BOUNCED, created_at=dt, bounced_email=bounced_email
        )

    class Meta:
        ordering = (
            "application__saved_on",
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
        DETAILS_CORRECTED = "detailscorrected", "Referee details corrected"
        EMAIL_TO_REFEREE_BOUNCED = "requestbounced", "Email to referee bounced"

    referee = models.ForeignKey(Referee, on_delete=models.CASCADE, related_name="actions")
    created_at = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)

    # user is user who triggered action, this can be null.
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)

    # For EMAIL_TO_REFEREE_BOUNCED only:
    bounced_email = models.CharField(default="", blank="")

    # This is set to True only for some records which had to be partially
    # invented in a database migration due to missing data. Any stats on this
    # table should exclude these records.
    inaccurate = models.BooleanField(default=False)

    @admin.display(ordering="referee__name")
    def referee_name(self) -> str:
        return self.referee.name

    @admin.display(
        ordering=Concat(
            "referee__application__officer__first_name", Value(" "), "referee__application__officer__last_name"
        )
    )
    def officer_name(self):
        return self.referee.application.officer.full_name

    class Meta:
        ordering = [("created_at")]

    def __repr__(self):
        return f"<ReferenceAction {self.action_type} {self.created_at} | {self.referee}>"

    @cached_property
    def extra_info(self) -> str:
        """
        Extra info for the action table
        """
        if self.action_type == ReferenceAction.ActionType.EMAIL_TO_REFEREE_BOUNCED:
            return f"Email: {self.bounced_email}"
        return ""


def empty_reference(reference: Reference) -> bool:
    return reference is None or reference.how_long_known.strip() == ""


class ReferenceManager(models.Manager):
    def get_queryset(self) -> QuerySet:
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
        "Please comment on aspects of the applicant's character (ie. Christian experience honesty, trustworthiness, reliability, disposition, faithful attendance at worship/prayer meetings.)"
    )
    concerns = models.TextField(
        "Have you ever had concerns about either this applicant's ability or suitability to work with children and young people?"
    )
    comments = models.TextField("Any other comments you wish to make", blank=True)
    given_in_confidence = models.BooleanField(
        help_text="""Is this reference given "in confidence"? If yes, in the case that the applicant wishes to see the contents of the references made about them under a GDPR "Right of access" request, we will exclude the contents of this reference. It is important to us that you feel at liberty to tell us any concerns you have about the applicant, so you may tick this box if you feel it is necessary.""",
        default=False,
    )
    created_on = models.DateField("date created")
    referee = models.OneToOneField(Referee, on_delete=models.CASCADE)

    previous_reference = models.ForeignKey(
        "Reference",
        null=True,
        blank=True,
        default=None,
        related_name="following_references",
        on_delete=models.PROTECT,
    )

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
        return f"Reference for {officer.full_name} by {self.referee_name} {self.created_on.year}"

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


def close_enough_referee_match(referee1: Referee, referee2: Referee):
    if (
        normalized_name(referee1.name).lower() == normalized_name(referee2.name).lower()
        and referee1.email.lower() == referee2.email.lower()
    ):
        return True

    return False


def add_previous_references(referee: Referee) -> None:
    """
    Adds the attributes:
    - 'previous_reference' (which is None if no exact match)
    - 'possible_previous_references' (list ordered by relevance)
    """
    exact, previous = get_previous_references(referee)
    referee.previous_reference = exact
    referee.possible_previous_references = [] if exact else previous


def get_previous_references(referee: Referee) -> tuple[Reference | None, list[Reference]]:
    # Look for References for same officer, within the previous five years.
    # Don't look for references from this year's application (which will be the
    # other referee).
    cutoffdate = referee.application.saved_on - timedelta(365 * 5)
    previous = list(
        Reference.objects.filter(
            referee__application__officer=referee.application.officer,
            referee__application__finished=True,
            created_on__gte=cutoffdate,
        )
        .select_related("referee__application")
        .exclude(referee__application=referee.application)
        .order_by("-referee__application__saved_on")
    )

    # Sort by relevance
    def relevance_key(reference):
        # Matching name or email address is better, so has lower value,
        # so it comes first.
        return -(
            int(reference.referee.email.lower() == referee.email.lower())
            + int(reference.referee.name.lower() == referee.name.lower())
        )

    previous.sort(key=relevance_key)  # sort is stable, so previous sort by date should be kept

    exact = None
    for reference in previous:
        if close_enough_referee_match(reference.referee, referee):
            exact = reference
            break
    return (exact, previous)
