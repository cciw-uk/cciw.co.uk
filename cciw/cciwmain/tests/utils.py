from cciw.cciwmain.common import get_thisyear, get_current_domain


def init_query_caches():
    """
    Initialise any cached values that do DB queries.

    This is useful to improve isolation of tests that check the number of queries used.
    """
    get_thisyear()
    get_current_domain()
