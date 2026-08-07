from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from django.db import models
from django.utils.functional import cached_property

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp

from .roles import CampRole


class InvitationQuerySet(models.QuerySet):
    def name_order(self):
        return self.order_by("officer__first_name", "officer__last_name", "officer__email")

    def for_future_camps(self, now: datetime) -> InvitationQuerySet:
        return self.filter(camp__end_date__gte=now)


class InvitationManager(models.Manager.from_queryset(InvitationQuerySet)):
    def get_queryset(self) -> InvitationQuerySet:
        # TODO we should work out if we really need to select all this always...
        return super().get_queryset().select_related("officer", "camp", "camp__chaplain")


class Invitation(models.Model):
    officer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="invitations")
    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="invitations")
    role = models.ForeignKey(CampRole, on_delete=models.PROTECT, null=True, blank=True, related_name="invitations")
    added_on = models.DateField("date added", default=date.today)
    notes = models.CharField(max_length=255, blank=True)

    objects = InvitationManager()

    class Meta:
        ordering = ("-camp__year", "officer__first_name", "officer__last_name")
        unique_together = (("officer", "camp"),)
        base_manager_name = "objects"

    def __str__(self):
        return f"{self.officer.full_name} — camp {self.camp}"


@dataclass(kw_only=True)
class CandidateOfficer:
    officer: User
    is_previous: bool
    previous_role: CampRole | None = None

    def __getattr__(self, attr):
        return getattr(self.officer, attr)


class OfficerList:
    """
    Utility to manage officers for a camp.
    Provides:
    - current invitations (officer + chosen role)
    - ordered list of chooseable officers, with previous role info

    Each user appears in only one list.
    """

    def __init__(self, camp: Camp) -> None:
        self.camp = camp

    # Public interface

    @cached_property
    def invitations(self) -> list[Invitation]:
        return self.camp.invitations.all().name_order().select_related("officer", "role")

    @cached_property
    def candidate_officers(self) -> list[CandidateOfficer]:
        """
        List of officers who can be added to a camp, with info about previous roles
        """
        # Order previously used officers before others.
        return [
            CandidateOfficer(
                officer=inv.officer,
                is_previous=True,
                previous_role=inv.role,
            )
            for inv in self._previous_invitations
            if inv.officer not in self._current_officers
        ] + [
            CandidateOfficer(
                officer=officer,
                is_previous=False,
            )
            for officer in self._other_officers
        ]

    @cached_property
    def addable_officers(self) -> list[User]:
        """
        List of officers who can be added to a camp
        """
        return [co.officer for co in self.candidate_officers]

    def get_previous_role(self, officer: User) -> CampRole | None:
        previous_invite = self._previous_invitation_dict.get(officer.id, None)
        if previous_invite is None:
            return None
        return previous_invite.role  # This too can be None

    # Private Implementation

    @cached_property
    def _current_officers(self) -> set[User]:
        return {inv.officer for inv in self.invitations}

    @cached_property
    def _previous_invitations(self) -> list[Invitation]:
        previous_camp = self.camp.previous_camp
        if previous_camp is not None:
            return previous_camp.invitations.all().name_order().select_related("officer", "role").name_order()
        else:
            return []

    @cached_property
    def _previous_but_not_current_officers(self) -> set[User]:
        return {inv.officer for inv in self._previous_invitations if inv.officer not in self._current_officers}

    @cached_property
    def _other_officers(self) -> list[User]:
        return list(
            User.objects.potential_officers()
            .exclude(id__in=[user.id for user in (self._current_officers | self._previous_but_not_current_officers)])
            .name_order()
        )

    @cached_property
    def _previous_invitation_dict(self):
        return {inv.officer_id: inv for inv in self._previous_invitations}


def add_officer_to_camp(camp: Camp, officer: User, role: CampRole) -> User:
    """
    Add officers to camp using CampRole. Returns officer added successfully.
    """
    inv, created = Invitation.objects.get_or_create(camp=camp, officer=officer, defaults=dict(role=role))
    if inv.role != role:
        inv.role = role
        inv.save()
    return officer


def remove_officer_from_camp(camp, officer: User) -> None:
    camp.invitations.filter(officer=officer).delete()
