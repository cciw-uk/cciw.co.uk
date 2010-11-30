from cciw.cciwmain.common import get_thisyear
from django.contrib.sites.models import Site


def init_query_caches():
    """
    Initialise any cached values that do DB queries.

    This is useful to improve isolation of tests that check the number of queries used.
    """
    get_thisyear()
    Site.objects.get_current()


class FuzzyInt(int):
    def __new__(cls, lowest, highest):
        obj = super(FuzzyInt, cls).__new__(cls, highest)
        obj.lowest = lowest
        obj.highest = highest
        return obj

    def __eq__(self, other):
        return other >= self.lowest and other <= self.highest

    def __repr__(self):
        return "[%d, %d]" % (self.lowest, self.highest)
