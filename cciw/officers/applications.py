from collections.abc import Sequence
from datetime import timedelta

from django.db.models import QuerySet
from django.template import loader

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.officers.models import Application, Invitation

# To enable Applications to be shared between camps, and in some cases to belong
# to no camps, there is no direct connection between a Camp and an Application.
# This means we need another way to associate them. We also need to have a
# concept of 'this year', so that an officer submits once application form 'per
# year'. To manage this logic we're using dates of camps (which are clustered in
# the summer) and the invitations to camp that am officer has.

# Logic for dates:
# - an application is considered valid for a camp/year if the saved_on
#   - is within 12 months of the start date of the camp/first camp that year
#   - is after the previous year's camps' end dates.
#
# i.e. we assume all camps happen in a cluster, and application forms are
# submitted in the period leading up to that cluster.


def thisyears_applications(user):
    """
    Returns a QuerySet containing the applications a user has that
    apply to 'this year', i.e. to camps still in the future.
    """
    first_camp_thisyear = Camp.objects.filter(year=common.get_thisyear()).order_by("start_date").first()
    apps = user.applications.all()

    if first_camp_thisyear is not None:
        apps = apps.filter(saved_on__gte=first_camp_thisyear.start_date - timedelta(365))
        past_camp = Camp.objects.filter(start_date__year=first_camp_thisyear.year - 1).order_by("-end_date").first()
    else:
        past_camp = Camp.objects.order_by("-end_date").first()

    if past_camp is not None:
        apps = apps.filter(saved_on__gt=past_camp.end_date)

    return apps


def invitations_for_application(application: Application) -> list[Invitation]:
    """
    Relevant Invitation objects for an application
    """
    if application.saved_on is None:
        return []
    # The connection between applications and camps is fuzzy,
    # because we want applications to be re-usable for multiple camps.

    # This means we have to "guess" based on date, which works fine in practice
    # because camps are all clumped together in summer.

    # Return invitations for camps that are after the application was submitted,
    # but not more than a year after.
    invitations = list(
        application.officer.invitations.filter(
            camp__start_date__gte=application.saved_on, camp__start_date__lt=application.saved_on + timedelta(365)
        ).select_related("camp", "role")
    )
    # For old applications, this could potentially return 2 years of invitations,
    # if the camp for the second year was earlier in the year than the first year.
    # So we filter for the first year.
    if len(invitations) > 0:
        invitations.sort(key=lambda i: i.camp.start_date)
        first_year = invitations[0].camp.year
        invitations = [i for i in invitations if i.camp.year == first_year]
    return invitations


def camps_for_application(application: Application) -> Sequence[Camp]:
    """
    For an Application, returns the camps it is relevant to, in terms of
    notifying people.
    """
    # We get all camps that are in the year following the application form
    # submitted date.
    invites = invitations_for_application(application)
    return [i.camp for i in invites]


def applications_for_camp(camp, officer_ids=None) -> QuerySet[Application]:
    """
    Returns the applications that are relevant for a camp.
    """
    return applications_for_camps([camp], officer_ids=officer_ids)


def applications_for_camps(camps, officer_ids=None) -> QuerySet[Application]:
    """
    Returns the applications that are relevant for a list of camps.
    """
    if not camps:
        return []
    if not all(camp.year == camps[0].year for camp in camps):
        raise AssertionError("This function can only be used if all camps in the same year")

    if officer_ids is None:
        # Use invitations to work out which officers we care about
        invitations = Invitation.objects.filter(camp__in=camps)
        officer_ids = invitations.values_list("officer_id", flat=True)
    apps = Application.objects.filter(finished=True, officer__in=officer_ids)

    earliest_date = min(camp.start_date for camp in camps) - timedelta(365)
    latest_date = max(camp.start_date for camp in camps)
    apps = apps.filter(saved_on__lte=latest_date, saved_on__gt=earliest_date)

    previous_years_last_camp = Camp.objects.filter(year=camps[0].year - 1).order_by("-end_date").first()
    if previous_years_last_camp is not None:
        # We have some previous camps
        apps = apps.filter(saved_on__gt=previous_years_last_camp.end_date)
    return apps


def application_to_text(app: Application) -> str:
    t = loader.get_template("cciw/officers/application_email.txt")
    return t.render({"app": app})


def application_to_rtf(app: Application) -> str:
    t = loader.get_template("cciw/officers/application.rtf")
    return t.render({"app": app})


def application_rtf_filename(app: Application) -> str:
    return _application_filename_stem(app) + ".rtf"


def application_txt_filename(app: Application) -> str:
    return _application_filename_stem(app) + ".txt"


def _application_filename_stem(app: Application) -> str:
    if app.saved_on is None:
        submitted = ""
    else:
        submitted = "_" + app.saved_on.strftime("%Y-%m-%d")
    return f"Application_{app.officer.username}{submitted}"
