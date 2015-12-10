from datetime import date

from django.core.urlresolvers import reverse
from django.test import TestCase

from cciw.cciwmain.common import get_thisyear
from cciw.cciwmain.models import Camp, CampName, Person, Site
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import FuzzyInt, init_query_caches
from cciw.sitecontent.models import HtmlChunk


class CampModel(TestCase):

    def setUp(self):
        l1 = Person.objects.create(name="John")
        l2 = Person.objects.create(name="Mary")
        l3 = Person.objects.create(name="Gregory")
        site = Site.objects.create(short_name="farm",
                                   slug_name="farm",
                                   long_name="The Farm")
        camp_name, _ = CampName.objects.get_or_create(
            name="Blue",
            slug="blue",
            color="#0000ff",
        )
        camp = Camp.objects.create(
            year=2013,
            camp_name=camp_name,
            minimum_age=11,
            maximum_age=17,
            start_date=date(2013, 6, 1),
            end_date=date(2013, 6, 9),
            max_campers=70,
            max_male_campers=40,
            max_female_campers=40,
            chaplain=l3,
            site=site,
        )
        camp.leaders.add(l1, l2)
        self.camp = camp

        camp_2 = Camp.objects.create(
            year=2014,
            camp_name=camp_name,
            minimum_age=11,
            maximum_age=17,
            start_date=date(2014, 6, 2),
            end_date=date(2014, 6, 10),
            max_campers=70,
            max_male_campers=40,
            max_female_campers=40,
            chaplain=l3,
            site=site,
        )
        self.camp_2 = camp_2

    def test_display(self):
        self.assertEqual(str(self.camp), "2013-blue (John, Mary, Gregory)")

    def test_names(self):
        self.assertEqual(self.camp.name, "Blue")
        self.assertEqual(self.camp.slug_name, "blue")
        self.assertEqual(self.camp.slug_name_with_year, "2013-blue")

    def test_previous_and_next(self):
        self.assertEqual(self.camp_2.previous_camp, self.camp)
        self.assertEqual(self.camp.next_camp, self.camp_2)

        self.assertEqual(self.camp.previous_camp, None)
        self.assertEqual(self.camp_2.next_camp, None)


class ThisyearPage(BasicSetupMixin, TestCase):

    def setUp(self):
        super().setUp()
        HtmlChunk.objects.create(name="camp_dates_intro_text")
        HtmlChunk.objects.create(name="camp_dates_outro_text")

    def test_get(self):
        init_query_caches()
        y = get_thisyear()
        site = Site.objects.get(id=1)

        for i in range(1, 20):
            cn = CampName.objects.create(name=chr(64 + i),
                                         slug=chr(64 + i).lower(),
                                         color="#0000" + hex(i)[2:])
            c = Camp.objects.create(year=y, site=site,
                                    camp_name=cn,
                                    minimum_age=11,
                                    maximum_age=17,
                                    start_date=date(y, 6, 1),
                                    end_date=date(y, 6, 8))
            p = Person.objects.create(name="Leader %s" % i)
            c.leaders.add(p)

        with self.assertNumQueries(FuzzyInt(1, 6)):
            resp = self.client.get(reverse('cciw-cciwmain-thisyear'))

        for c in Camp.objects.filter(year=y):
            self.assertContains(resp, c.get_absolute_url())
