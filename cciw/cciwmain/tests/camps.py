from datetime import date

from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp, Site, Person
from cciw.cciwmain.tests.utils import init_query_caches, FuzzyInt
from cciw.sitecontent.models import HtmlChunk


class CampModel(TestCase):

    def setUp(self):
        l1 = Person.objects.create(name="John")
        l2 = Person.objects.create(name="Mary")
        l3 = Person.objects.create(name="Gregory")
        site = Site.objects.create(short_name="farm",
                                   slug_name="farm",
                                   long_name="The Farm")

        camp = Camp.objects.create(
            year=2013,
            number=1,
            minimum_age=11,
            maximum_age=17,
            start_date=date(2013,6,1),
            end_date=date(2013,6,9),
            max_campers=70,
            max_male_campers=40,
            max_female_campers=40,
            chaplain=l3,
            site=site,
            )
        camp.leaders.add(l1, l2)
        self.camp = camp

    def test_display(self):
        self.assertEqual(unicode(self.camp), u"2013-1 (John, Mary, Gregory)")


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
