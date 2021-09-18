from cciw.cciwmain.models import Camp
from cciw.officers.stats import get_camp_officer_stats, get_camp_officer_stats_trend
from cciw.officers.tests.base import ExtraOfficersSetupMixin
from cciw.utils.tests.base import TestBase


class StatsTests(ExtraOfficersSetupMixin, TestBase):

    # Very basic tests here, should expand

    def test_get_camp_officer_stats(self):
        results = get_camp_officer_stats(self.default_camp_1)
        assert results['Officers'].max() == 3  # 3 officers invited
        assert results['Officers'].min() == 0

    def test_get_camp_officer_stats_trend(self):
        camps = list(Camp.objects.all().order_by('year'))
        results = get_camp_officer_stats_trend(camps[0].year, camps[-1].year)
        assert results['Officer count'].to_dict() == \
            {2000: 3, 2001: 0}
