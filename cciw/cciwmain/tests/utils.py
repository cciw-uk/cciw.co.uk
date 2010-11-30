from cciw.cciwmain.common import get_thisyear
from django.contrib.sites.models import Site

def init_query_caches():
    """
    Initialise any cached values that do DB queries.

    This is useful to improve isolation of tests that check the number of queries used.
    """
    get_thisyear()
    Site.objects.get_current()
