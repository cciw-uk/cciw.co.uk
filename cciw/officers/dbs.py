import operator
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import reduce
from typing import Optional

from django.utils import timezone

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.officers.applications import applications_for_camps
from cciw.officers.models import Application, DBSActionLog, DBSCheck, Invitation


@dataclass
class DBSNumber:
    number: str
    previous_check_good: Optional[bool]  # True = good, False = bad, None = unknown


@dataclass
class DBSInfo:
    camps: list[Camp]
    has_application_form: bool
    application_id: int
    has_dbs: bool
    has_recent_dbs: bool
    last_dbs_form_sent: Optional[datetime]
    last_leader_alert_sent: Optional[datetime]
    last_form_request_sent: Optional[datetime]
    address: str
    birth_date: date
    dbs_check_consent: bool
    update_enabled_dbs_number: Optional[str]
    last_dbs_rejected: bool

    @property
    def applicant_rejected(self) -> bool:
        return self.last_dbs_rejected or (
            self.update_enabled_dbs_number is not None and self.update_enabled_dbs_number.previous_check_good is False
        )

    @property
    def requires_action(self) -> bool:
        return self.requires_alert_leaders or self.requires_send_dbs_form_or_request or self.applicant_rejected

    @property
    def _action_possible(self):
        return not self.has_recent_dbs and self.has_application_form

    @property
    def requires_alert_leaders(self) -> bool:
        return self._action_possible and not self.dbs_check_consent and not self.last_leader_alert_sent

    @property
    def requires_send_dbs_form_or_request(self) -> bool:
        return (
            self._action_possible
            and self.dbs_check_consent
            and (self.last_dbs_form_sent is None and self.last_form_request_sent is None)
        )

    @property
    def can_register_received_dbs_form(self) -> bool:
        return not self.applicant_rejected and self._action_possible

    @property
    def can_check_dbs_online(self):
        return (
            self._action_possible
            and not self.applicant_rejected
            and (
                self.update_enabled_dbs_number is not None
                and self.update_enabled_dbs_number.previous_check_good is True
            )
        )


def get_officers_with_dbs_info_for_camps(camps, officer_id: int = None) -> list[tuple[User, DBSInfo]]:
    """
    Get needed DBS officer info for the given set of camps,
    return a list of two tuples, [(officer, dbs_info)]
    """
    # Some of this logic could be put onto specific models. However, we only
    # ever need this info in bulk for specific views, and efficient data access
    # patterns look completely different for the bulk case. So we use this
    # utility function.
    # We need all the officers, and we need to know which camp(s) they belong
    # to. Even if we have only selected one camp, it might be nice to know if
    # they are on other camps. So we get data for all camps, and filter later.
    # We also want to be able to do filtering by javascript in the frontend.
    now = timezone.now()

    camp_invitations = Invitation.objects.filter(camp__in=camps).select_related("officer", "camp__camp_name")
    if officer_id is not None:
        camp_invitations = camp_invitations.filter(officer__id=officer_id)
    camp_invitations = list(camp_invitations)

    all_officers = list({i.officer for i in camp_invitations})
    all_officers.sort(key=lambda o: (o.first_name, o.last_name))
    apps = list(applications_for_camps(camps))
    recent_dbs_officer_ids = set(
        reduce(operator.or_, [DBSCheck.objects.get_for_camp(c, include_late=True) for c in camps]).values_list(
            "officer_id", flat=True
        )
    )

    all_dbs_officer_ids = set(DBSCheck.objects.filter(officer__in=all_officers).values_list("officer_id", flat=True))

    last_dbs_status = dict(
        DBSCheck.objects.filter(officer__in=all_dbs_officer_ids).values_list("officer_id", "applicant_accepted")
    )

    # Looking for action logs: set cutoff to a year before now, on the basis that
    # anything more than that will have been lost or irrelevant, and we don't
    # want to load everything into memory.
    relevant_action_logs = (
        DBSActionLog.objects.filter(officer__in=all_officers)
        .filter(created_at__gt=now - timedelta(365))
        .order_by("created_at")
    )
    dbs_forms_sent = list(relevant_action_logs.filter(action_type=DBSActionLog.ACTION_FORM_SENT))
    requests_for_dbs_form_sent = list(
        relevant_action_logs.filter(action_type=DBSActionLog.ACTION_REQUEST_FOR_DBS_FORM_SENT)
    )
    leader_alerts_sent = list(relevant_action_logs.filter(action_type=DBSActionLog.ACTION_LEADER_ALERT_SENT))

    update_service_dbs_numbers_for_officers = get_update_service_dbs_numbers(all_officers)

    # Work out, without doing any more queries:
    # - which camps each officer is on
    # - if they have an application form
    # - if they have an up to date DBS
    # - when the last DBS form was sent to officer
    # - when the last alert was sent to leader

    officers_camps = defaultdict(list)
    for invitation in camp_invitations:
        officers_camps[invitation.officer_id].append(invitation.camp)

    officer_apps = {a.officer_id: a for a in apps}

    def logs_to_dict(logs) -> dict[int, datetime]:
        # NB: order_by('created_at') above means that requests sent later will overwrite
        # those sent earlier in the following dictionary
        return {f.officer_id: f.created_at for f in logs}

    dbs_forms_sent_for_officers = logs_to_dict(dbs_forms_sent)
    requests_for_dbs_form_sent_for_officers = logs_to_dict(requests_for_dbs_form_sent)
    leader_alerts_sent_for_officers = logs_to_dict(leader_alerts_sent)

    retval = []
    for o in all_officers:
        officer_camps = officers_camps[o.id]
        app = officer_apps.get(o.id, None)
        dbs_info = DBSInfo(
            camps=officer_camps,
            has_application_form=app is not None,
            application_id=app.id if app is not None else None,
            has_dbs=o.id in all_dbs_officer_ids,
            has_recent_dbs=o.id in recent_dbs_officer_ids,
            last_dbs_form_sent=dbs_forms_sent_for_officers.get(o.id),
            last_leader_alert_sent=leader_alerts_sent_for_officers.get(o.id),
            last_form_request_sent=requests_for_dbs_form_sent_for_officers.get(o.id),
            address=app.one_line_address if app is not None else "",
            birth_date=app.birth_date if app is not None else None,
            dbs_check_consent=app.dbs_check_consent if app is not None else False,
            update_enabled_dbs_number=update_service_dbs_numbers_for_officers.get(o.id),
            last_dbs_rejected=not last_dbs_status[o.id] if o.id in last_dbs_status else False,
        )
        retval.append((o, dbs_info))
    return retval


def get_update_service_dbs_numbers(officers):
    # Find DBS numbers than can be used with the update service.
    # Two sources:
    # 1) DBSCheck
    # 2) ApplicationForm

    # We also need to know, for a given DBS number, what the status of any
    # previous check was, or if none has been done, because the update service
    # only tells us what has changed since last time, not what was originally
    # listed.

    # These may or may not be update-service registered
    dbs_checks = DBSCheck.objects.filter(officer__in=officers).order_by("completed")  # most recent last

    update_service_dbs_numbers = []
    applicant_accepted_dict = {}
    for dbs_check in dbs_checks:
        dbs_number = dbs_check.dbs_number.strip()
        # Most recent last means most recent wins in the case of duplicates.
        # For online check, we count 'bad' (we saw something bad on
        # an update), but only count 'good' for the full form.
        if dbs_check.check_type == DBSCheck.CheckType.FORM:
            applicant_accepted_dict[dbs_number] = dbs_check.applicant_accepted
        elif dbs_check.check_type == DBSCheck.CheckType.ONLINE and not dbs_check.applicant_accepted:
            applicant_accepted_dict[dbs_number] = dbs_check.applicant_accepted

        if dbs_check.registered_with_dbs_update:
            update_service_dbs_numbers.append((dbs_check.completed, dbs_check.officer_id, dbs_number))

    # According to instructions given officers, these should all be
    # update-service registered
    update_service_dbs_numbers_from_application_form = (
        Application.objects.filter(officer__in=officers, finished=True)
        .exclude(dbs_number="")
        .order_by("date_saved")  # most recent last
        .values_list("officer_id", "dbs_number", "date_saved")
    )

    for o_id, dbs_number, completed in update_service_dbs_numbers_from_application_form:
        dbs_number = dbs_number.strip()
        update_service_dbs_numbers.append((completed, o_id, dbs_number))

    retval = {}

    update_service_dbs_numbers.sort()  # by date submitted, ascending
    for (
        dt,
        officer_id,
        dbs_number,
    ) in update_service_dbs_numbers:
        # Most recent last means most recent wins in the case of more than one for officer:
        retval[officer_id] = DBSNumber(
            number=dbs_number.strip(), previous_check_good=applicant_accepted_dict.get(dbs_number)
        )
    return retval
