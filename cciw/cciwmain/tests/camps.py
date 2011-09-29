from datetime import date

from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp, Site, Person
from cciw.cciwmain.tests.utils import init_query_caches, FuzzyInt
from cciw.sitecontent.models import HtmlChunk


class ThisyearPage(TestCase):

    fixtures = ['basic.json', 'htmlchunks.json']

    def test_get(self):
        init_query_caches()
        y = get_thisyear()
        site = Site.objects.get(id=1)

        for i in range(1, 20):
            c = Camp.objects.create(year=y, number=i, site=site,
                                    minimum_age=11,
                                    maximum_age=17,
                                    start_date=date(y, 6, 1),
                                    end_date=date(y, 6, 8))
            p = Person.objects.create(name="Leader %s" % i)
            c.leaders.add(p)

        with self.assertNumQueries(FuzzyInt(1, 6)):
            resp = self.client.get(reverse('cciw.cciwmain.views.camps.thisyear'))

        for c in Camp.objects.filter(year=y):
            self.assertContains(resp, c.get_absolute_url())
