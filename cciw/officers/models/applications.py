from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Prefetch
from django.utils.functional import cached_property

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.utils.models import ClearCachedPropertyMixin

from ...officers.fields import (
    RequiredCharField,
    RequiredDateField,
    RequiredEmailField,
    RequiredExplicitBooleanField,
    RequiredTextField,
)
from .common import NAME_LENGTH

if TYPE_CHECKING:
    from .references import Referee


class ApplicationQuerySet(models.QuerySet):
    def older_than(self, before_datetime: datetime) -> ApplicationQuerySet:
        return self.filter(saved_on__lt=before_datetime.date())

    def not_in_use(self, now: datetime) -> ApplicationQuerySet:
        return self.exclude(officer__id__in=User.objects.in_use(now))

    def with_references(self) -> models.QuerySet:
        from .references import Referee

        return self.prefetch_related(Prefetch("referee_set", queryset=Referee.objects.select_related("reference")))


class ApplicationManagerBase(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("officer")


ApplicationManager = ApplicationManagerBase.from_queryset(ApplicationQuerySet)


class Application(ClearCachedPropertyMixin, models.Model):
    """
    Officer's application form, required to come on camp.
    """

    officer = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, related_name="applications"
    )  # blank=True to get the admin to work
    full_name = RequiredCharField("full name", max_length=NAME_LENGTH)
    birth_date = RequiredDateField("date of birth", null=True, default=None)
    birth_place = RequiredCharField("place of birth", max_length=100)
    address_firstline = RequiredCharField("address", max_length=100)
    address_town = RequiredCharField(
        "town/city", max_length=60
    )  # 60 == len("Llanfairpwllgwyngyllgogerychwyrndrobwyll-llantysiliogogogoch")
    address_county = RequiredCharField("county", max_length=100)
    address_postcode = RequiredCharField("post code", max_length=10)
    address_country = RequiredCharField("country", max_length=100)
    address_tel = RequiredCharField("telephone", max_length=30, blank=True)  # +44-(0)1224-XXXX-XXXX
    address_mobile = models.CharField("mobile", max_length=30, blank=True)
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
    saved_on = models.DateField("date saved", null=True, blank=True)

    erased_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = ApplicationManager()

    class Meta:
        ordering = (
            "-saved_on",
            "officer__first_name",
            "officer__last_name",
        )
        base_manager_name = "objects"

    @cached_property
    def referees(self) -> tuple[Referee, Referee]:
        """A cached version of 2 items that can exist in 'references_set', which
        are created if they don't exist. Read only"""
        return (self._referee(1), self._referee(2))

    @property
    def one_line_address(self) -> str:
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

    def __str__(self) -> str:
        if self.saved_on is not None:
            submitted = ("submitted " if self.finished else "saved ") + self.saved_on.strftime("%Y-%m-%d")
        else:
            submitted = "incomplete"
        return f"Application from {self.full_name} ({submitted})"

    def _referee(self, num: int) -> Referee:
        if hasattr(self, "_prefetched_objects_cache"):
            if "referee_set" in self._prefetched_objects_cache:
                vals = [v for v in self._prefetched_objects_cache["referee_set"] if v.referee_number == num]
                if len(vals) == 1:
                    return vals[0]
        return self.referee_set.get_or_create(referee_number=num)[0]

    def could_be_for_camp(self, camp: Camp) -> bool:
        # An application is 'for' a camp if it is submitted in the year before
        # the camp start date. Logic duplicated in applications_for_camp
        return self.saved_on <= camp.start_date and self.saved_on > camp.start_date - timedelta(days=365)

    def clear_out_old_unfinished(self):
        # This is called when an application is created and saved by the
        # officer. In some cases it could be when a leader is editing old
        # application form of their own, in which case we don't want to delete a
        # currently in progress more recent application form.

        others = self.officer.applications.exclude(id=self.id)
        unfinished = others.filter(finished=False)
        unsaved = unfinished.filter(saved_on__isnull=True)

        # We can definitely delete all other old unsaved applications:
        to_delete = unsaved

        # We can also delete any unfinished application forms with
        # a saved_on before this one:
        if self.saved_on is not None:
            unfinshed_saved_earlier = unfinished.filter(saved_on__lt=self.saved_on)
            to_delete = to_delete | unfinshed_saved_earlier
        to_delete.delete()


class QualificationType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


class Qualification(models.Model):
    application = models.ForeignKey(Application, related_name="qualifications", on_delete=models.CASCADE)
    type = models.ForeignKey(QualificationType, related_name="qualifications", on_delete=models.PROTECT)
    issued_on = models.DateField("date issued")

    def __str__(self) -> str:
        return f"{self.type} qualification for {self.application.officer}"

    def copy(self, **kwargs) -> Qualification:
        q = Qualification()
        q.application = self.application
        q.type = self.type
        q.issued_on = self.issued_on
        for k, v in kwargs.items():
            setattr(q, k, v)
        return q

    class Meta:
        ordering = ["application", "type__name"]
        unique_together = [("application", "type")]
