import pytest

from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.stats import get_camp_officer_stats, get_camp_officer_stats_trend
from cciw.officers.tests import factories as officer_factories


@pytest.mark.django_db
def test_get_camp_officer_stats():
    camp = camp_factories.create_camp(officers=[officer_factories.create_officer() for _ in range(0, 3)])
    results = get_camp_officer_stats(camp)
    assert results["Officers"].max() == 3
    assert results["Officers"].min() == 0


@pytest.mark.django_db
def test_get_camp_officer_stats_trend():
    camp_factories.create_camp(year=2010, officers=[officer_factories.create_officer() for _ in range(0, 3)])
    camp_factories.create_camp(year=2011, officers=[officer_factories.create_officer() for _ in range(0, 2)])
    camp_factories.create_camp(year=2012)
    results = get_camp_officer_stats_trend(2010, 2012)
    assert results["Officer count"].to_dict() == {2010: 3, 2011: 2, 2012: 0}
