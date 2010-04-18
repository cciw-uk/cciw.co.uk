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
    Returns list of officers who have not filled out application form
    """
    finished_apps_off_ids = [o['officer__id']
                             for o in camp.application_set.filter(finished=True).values('officer__id')]
    return list(camp.officers.order_by('first_name', 'last_name', 'email').exclude(id__in=finished_apps_off_ids))

