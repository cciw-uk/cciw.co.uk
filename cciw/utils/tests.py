"""
Tests for utils functions
"""

import pytest

from cciw.cciwmain.utils import make_content_disposition_safe_filename
from cciw.cciwmain.views.sites import index as site_index
from cciw.utils.views import url_matches_view_function


def test_url_matches_view_function():
    assert url_matches_view_function("/sites/", site_index)
    assert url_matches_view_function("/sites/", site_index)
    assert not url_matches_view_function("/sites-x/", site_index)

    assert url_matches_view_function("/sites/?foo=bar", site_index)


@pytest.mark.parametrize(
    "filename,sanitised",
    [
        ("hello there.txt", "hello there.txt"),
        ("école.html", "ecole.html"),
        ("teşekkürler.pdf", "tesekkurler.pdf"),
        ("'\"stuff.xlsx\n ", "stuff.xlsx"),
    ],
)
def test_make_content_disposition_safe_filename(filename: str, sanitised: str):
    assert make_content_disposition_safe_filename(filename) == sanitised
