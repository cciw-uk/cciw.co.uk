import datetime

from django import template
from django.template import loader

from cciw.cciwmain.models import Camp
from cciw.officers.models import Application

# To enable Applications to be shared between camps, and in some cases to belong
# to no camps, there is no direct connection between a Camp and an Application.
# This means we need another way to do it, and we're using dates.

# Logic for dates:
# - an application is considered valid for a camp/year if the date_submitted
#   - is within 12 months of the start date of the camp/first camp that year
#   - is after the previous year's camps' end dates.

def thisyears_applications(user):
    """
    Returns a QuerySet containing the applications a user has that
    apply to 'this year', i.e. to camps still in the future.
    """
    from cciw.officers.models import Camp
    future_camps = Camp.objects.filter(start_date__gte=datetime.date.today())
    apps = user.application_set.all()
    future_camp = None
    try:
        future_camp = future_camps[0]
    except IndexError:
        pass

    if future_camp is not None:
        apps = apps.filter(date_submitted__gte=future_camp.start_date - datetime.timedelta(365))
        past_camps = Camp.objects.filter(start_date__year=future_camp.year - 1)\
            .order_by('-end_date')
    else:
        past_camps = Camp.objects.order_by('-end_date')

    past_camp = None
    try:
        past_camp = past_camps[0]
    except IndexError:
        pass

    if past_camp is not None:
        apps = apps.filter(date_submitted__gt=past_camp.end_date)

    return apps

def camps_for_application(application):
    """
    For an Application, returns the camps it is relevant to, in terms of
    notifying people.
    """
    # We get all camps that are in the year following the application form
    # submitted date.
    if application.date_submitted is None:
        return []
    invites = application.officer.invitation_set.filter(camp__start_date__gte=application.date_submitted,
                                                        camp__start_date__lt=application.date_submitted +
                                                        datetime.timedelta(365))
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


def applications_for_camp(camp):
    """
    Returns the applications that are relevant for a camp.
    """
    # Use invitations to work out which officers we care about
    officer_ids = camp.invitation_set.values_list('officer_id', flat=True)
    apps = Application.objects.filter(finished=True,
                                      officer__in=officer_ids)

    apps = apps.filter(date_submitted__lte=camp.start_date,
                       date_submitted__gt=camp.start_date - datetime.timedelta(365))

    previous_camps = Camp.objects.filter(year=camp.year - 1)\
        .order_by('-end_date')
    last = None
    try:
        last = previous_camps[0]
    except IndexError:
        pass
    if last is not None:
        # We have some previous camps
        apps = apps.filter(date_submitted__gt=last.end_date)
    return apps


def application_to_text(app):
    t = loader.get_template('cciw/officers/application_email.txt');
    return t.render(template.Context({'app': app}))

def application_to_rtf(app):
    t = loader.get_template('cciw/officers/application.rtf');
    return t.render(template.Context({'app': app}))

def application_rtf_filename(app):
    return _application_filename_stem(app) + ".rtf"

def application_txt_filename(app):
    return _application_filename_stem(app) + ".txt"

def _application_filename_stem(app):
    if app.date_submitted is None:
        submitted = ''
    else:
        submitted = '_' + app.date_submitted.strftime('%Y-%m-%d')
    return 'Application_%s%s' % (app.officer.username, submitted)

def application_difference(app1, app2):
    from diff_match_patch import diff_match_patch
    differ = diff_match_patch()
    diffs = differ.diff_main(application_to_text(app1),
                             application_to_text(app2))
    differ.diff_cleanupSemantic(diffs)
    html = differ.diff_prettyHtml(diffs)
    # It looks better without the '&para;'
    html = html.replace('&para;', '')

    # Use custom colours etc.
    html = html.replace('background:#E6FFE6;', '')
    html = html.replace('background:#FFE6E6;', '')
    html = html.replace(' STYLE=""', '')

    return """<html>
<style>
body {
    font-family:monospace;
}

ins {
    background: #51FF17;
    text-decoration: none;
    font-weight: bold;
}

del {
   background: #FF6989;
   text-decoration: strike-through;
}
</style>
<body><pre>%s</pre></body></html>""" % html
