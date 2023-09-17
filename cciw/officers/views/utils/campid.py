from django.http import Http404

from cciw.cciwmain.common import CampId
from cciw.cciwmain.models import Camp


def get_camp_or_404(camp_id: CampId) -> Camp:
    try:
        return Camp.objects.by_camp_id(camp_id).get()
    except (Camp.DoesNotExist, ValueError):
        raise Http404
