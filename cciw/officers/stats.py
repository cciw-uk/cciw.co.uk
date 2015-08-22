from datetime import date, timedelta

from django.conf import settings

from cciw.officers.applications import applications_for_camp
from cciw.officers.models import ReferenceForm, CRBApplication


def get_camp_officer_stats(camps):
    stats = []
    for camp in camps:
        stat = {}
        # For efficiency, we are careful about what DB queries we do and what is
        # done in Python.
        stat['camp'] = camp

        invited_officers = list(camp.invitations.all().order_by('date_added').values_list('officer_id', 'date_added'))
        application_forms = list(applications_for_camp(camp).order_by('date_submitted').values_list('id', 'date_submitted'))

        officer_ids = [o[0] for o in invited_officers]
        officer_dates = [o[1] for o in invited_officers]
        app_ids = [a[0] for a in application_forms]
        app_dates = [a[1] for a in application_forms]
        ref_dates = list(ReferenceForm.objects.filter(reference_info__application__in=app_ids).order_by('date_created').values_list('date_created', flat=True))
        all_crb_info = list(CRBApplication.objects.filter(officer__in=officer_ids,
                                                          completed__lte=camp.start_date
                                                          ).order_by('completed').values_list('officer_id', 'completed'))
        # We duplicate logic from CRBApplication.get_for_camp here to avoid
        # duplicating queries
        valid_crb_info = [(off_id, d) for off_id, d in all_crb_info
                          if d >= camp.start_date - timedelta(days=settings.CRB_VALID_FOR)]
        # Make a plot by going through each day in the year before the camp and
        # incrementing a counter. This requires the data to be sorted already,
        # as above.
        graph_start_date = camp.start_date - timedelta(365)
        graph_end_date = min(camp.start_date, date.today())
        a = 0  # applications
        r = 0  # references
        o = 0  # officers
        v_idx = 0  # valid CRBs - index into valid_crb_info
        c_idx = 0  # CRBs       - index into all_crb_info
        v_tot = 0  #            - total for valid CRBs
        c_tot = 0  #            - total for all CRBs
        app_dates_data = []
        ref_dates_data = []
        officer_dates_data = []
        all_crb_dates_data = []
        _all_crb_seen_officers = set()
        valid_crb_dates_data = []
        _valid_crb_seen_officers = set()
        d = graph_start_date
        while d <= graph_end_date:
            # Application forms
            while a < len(app_dates) and app_dates[a] <= d:
                a += 1
            # References
            while r < len(ref_dates) and ref_dates[r] <= d:
                r += 1
            # Officers
            while o < len(officer_dates) and officer_dates[o] <= d:
                o += 1

            # CRBs: there can be multiple CRBs for each officer. If we've
            # already seen one, we don't increase the count.

            # Valid CRBs
            while v_idx < len(valid_crb_info) and valid_crb_info[v_idx][1] <= d:
                off_id = valid_crb_info[v_idx][0]
                v_idx += 1
                if off_id not in _valid_crb_seen_officers:
                    v_tot += 1
                    _valid_crb_seen_officers.add(off_id)
            # CRBs
            while c_idx < len(all_crb_info) and all_crb_info[c_idx][1] <= d:
                off_id = all_crb_info[c_idx][0]
                c_idx += 1
                if off_id not in _all_crb_seen_officers:
                    c_tot += 1
                    _all_crb_seen_officers.add(off_id)
            # Formats are those needed by 'flot' library
            ts = date_to_js_ts(d)
            app_dates_data.append([ts, a])
            ref_dates_data.append([ts, r / 2.0])
            officer_dates_data.append([ts, o])
            all_crb_dates_data.append([ts, c_tot])
            valid_crb_dates_data.append([ts, v_tot])
            d = d + timedelta(1)
        stat['application_dates_data'] = app_dates_data
        stat['reference_dates_data'] = ref_dates_data
        stat['all_crb_dates_data'] = all_crb_dates_data
        stat['valid_crb_dates_data'] = valid_crb_dates_data
        # Project officer list graphs at either end, to make the graph stretch that far.
        officer_dates_data.insert(0, [date_to_js_ts(graph_start_date), 0])
        officer_dates_data.append([date_to_js_ts(camp.start_date), len(officer_ids)])
        stat['officer_list_data'] = officer_dates_data
        stats.append(stat)

    return stats


def date_to_js_ts(d):
    """
    Converts a date object to the timestamp required by the flot library
    """
    return int(d.strftime('%s')) * 1000
