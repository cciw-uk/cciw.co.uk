"""
Utility functions for officers app.
"""

def camp_officer_list(camp):
    """
    Returns complete list of officers for a camp
    """
    return [i.officer for i in camp.invitation_set.all().select_related('officer')]

def camp_slacker_list(camp):
    """
    Returns list of officers who have not filled out application form
    """
    finished_apps_off_ids = [o['officer__id']
                             for o in camp.application_set.filter(finished=True).values('officer__id')]
    return [i.officer for i in camp.invitation_set.exclude(officer__in=finished_apps_off_ids).select_related('officer')]

