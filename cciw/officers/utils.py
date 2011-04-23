"""
Utility functions for officers app.
"""


def camp_officer_list(camp):
    """
    Returns complete list of officers for a camp
    """
    return list(camp.officers.all().order_by('first_name', 'last_name', 'email'))


def camp_slacker_list(camp):
    """
    Returns list of officers who have not filled out an application form
    """
    from cciw.officers.applications import applications_for_camp
    finished_apps_ids = applications_for_camp(camp).values_list('officer__id', flat=True)
    return list(camp.officers.order_by('first_name', 'last_name', 'email').exclude(id__in=finished_apps_ids))

