from django.test import TestCase

from cciw.cciwmain.models import Camp
from cciw.officers.stats import get_camp_officer_stats, get_camp_officer_stats_trend
from cciw.officers.tests.base import ExtraOfficersSetupMixin


class StatsTests(ExtraOfficersSetupMixin, TestCase):

    # Very basic tests here, should expand

    def test_get_camp_officer_stats(self):
        results = get_camp_officer_stats(self.default_camp_1)
        self.assertEqual(results['Officers'].max(), 3)  # 3 officers invited
        self.assertEqual(results['Officers'].min(), 0)

    def test_get_camp_officer_stats_trend(self):
        camps = list(Camp.objects.all().order_by('year'))
        results = get_camp_officer_stats_trend(camps[0].year, camps[-1].year)
        self.assertEqual(
            results['Officer count'].to_dict(),
            {2000: 3, 2001: 0}
        )
