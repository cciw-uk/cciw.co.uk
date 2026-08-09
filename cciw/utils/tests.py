"""
Tests for utils functions
"""

from cciw.cciwmain.views.sites import index as site_index
from cciw.utils.views import url_matches_view_function


def test_url_matches_view_function():
    assert url_matches_view_function("/sites/", site_index)
    assert url_matches_view_function("/sites/", site_index)
    assert not url_matches_view_function("/sites-x/", site_index)

    assert url_matches_view_function("/sites/?foo=bar", site_index)
