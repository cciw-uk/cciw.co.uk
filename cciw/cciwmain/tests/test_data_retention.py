from datetime import timedelta

import pytest

from cciw.data_retention import parse_keep


def test_parse_keep_forever():
    assert parse_keep('forever') is None


def test_parse_keep_years():
    assert parse_keep('3 years') == timedelta(days=3 * 365)


def test_parse_keep_other():
    with pytest.raises(ValueError):
        parse_keep('abc 123')
