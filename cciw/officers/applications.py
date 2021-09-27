from datetime import timedelta

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
# - an application is considered valid for a camp/year if the date_saved
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
        apps = apps.filter(date_saved__gte=first_camp_thisyear.start_date - timedelta(365))
        past_camp = Camp.objects.filter(start_date__year=first_camp_thisyear.year - 1).order_by("-end_date").first()
    else:
        past_camp = Camp.objects.order_by("-end_date").first()

    if past_camp is not None:
        apps = apps.filter(date_saved__gt=past_camp.end_date)

    return apps


def camps_for_application(application):
    """
    For an Application, returns the camps it is relevant to, in terms of
    notifying people.
    """
    # We get all camps that are in the year following the application form
    # submitted date.
    if application.date_saved is None:
        return []
    invites = application.officer.invitations.filter(
        camp__start_date__gte=application.date_saved, camp__start_date__lt=application.date_saved + timedelta(365)
    )
    # In some cases, the above query can catch two years of camps.  We only want
    # to the first year. (This doesn't matter very much, as
    # camps_for_application is used for notifications, and they only happen when
    # application forms are completed, and the following camps don't exist in
    # the database). But we try to handle correctly anyway.
    camps = [i.camp for i in invites]
    if len(camps) > 0:
        camps.sort(key=lambda c: c.start_date)
        first_year = camps[0].year
        camps = [c for c in camps if c.year == first_year]
    return camps


def applications_for_camp(camp, officer_ids=None):
    """
    Returns the applications that are relevant for a camp.
    """
    return applications_for_camps([camp], officer_ids=officer_ids)


def applications_for_camps(camps, officer_ids=None):
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
    apps = apps.filter(date_saved__lte=latest_date, date_saved__gt=earliest_date)

    previous_years_last_camp = Camp.objects.filter(year=camps[0].year - 1).order_by("-end_date").first()
    if previous_years_last_camp is not None:
        # We have some previous camps
        apps = apps.filter(date_saved__gt=previous_years_last_camp.end_date)
    return apps


def application_to_text(app):
    t = loader.get_template("cciw/officers/application_email.txt")
    return t.render({"app": app})


def application_to_rtf(app):
    t = loader.get_template("cciw/officers/application.rtf")
    return t.render({"app": app})


def application_rtf_filename(app):
    return _application_filename_stem(app) + ".rtf"


def application_txt_filename(app):
    return _application_filename_stem(app) + ".txt"


def _application_filename_stem(app):
    if app.date_saved is None:
        submitted = ""
    else:
        submitted = "_" + app.date_saved.strftime("%Y-%m-%d")
    return f"Application_{app.officer.username}{submitted}"
