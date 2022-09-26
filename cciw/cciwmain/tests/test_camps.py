from django.urls import reverse

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.base import BasicSetupMixin
from cciw.cciwmain.tests.utils import FuzzyInt, init_query_caches
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.tests.base import TestBase

from .base import factories


class CampModel(TestBase):
    def test_names(self):
        camp = factories.create_camp(
            year=2013,
            camp_name="Blue",
            leaders=[
                factories.create_person(name="John"),
                factories.create_person(name="Mary"),
            ],
            chaplain=factories.create_person(name="Gregory"),
        )
        assert str(camp) == "2013-blue (John, Mary, Gregory)"
        assert camp.name == "Blue"
        assert camp.slug_name == "blue"
        assert str(camp.url_id) == "2013-blue"

    def test_previous_and_next(self):
        camp = factories.create_camp(year=2013, camp_name="Blue")
        camp_2 = factories.create_camp(year=2014, camp_name="Blue")

        assert camp.next_camp == camp_2
        assert camp.previous_camp is None
        assert camp_2.next_camp is None
        assert camp_2.previous_camp == camp


class ThisyearPage(BasicSetupMixin, TestBase):
    def setUp(self):
        super().setUp()
        HtmlChunk.objects.create(name="camp_dates_intro_text")
        HtmlChunk.objects.create(name="camp_dates_outro_text")

    def test_get(self):
        init_query_caches()
        year = common.get_thisyear()
        for i in range(0, 20):
            factories.create_camp(year=year, leader=factories.get_any_camp_leader())
        with self.assertNumQueries(FuzzyInt(1, 8)):
            resp = self.client.get(reverse("cciw-cciwmain-thisyear"))

        for c in Camp.objects.filter(year=year):
            self.assertContains(resp, c.get_absolute_url())


class IndexPage(BasicSetupMixin, TestBase):
    def test_get(self):
        init_query_caches()
        year = common.get_thisyear()
        for i in range(0, 20):
            factories.create_camp(year=year, leader=factories.get_any_camp_leader())

        with self.assertNumQueries(FuzzyInt(1, 6)):
            resp = self.client.get(reverse("cciw-cciwmain-camps_year_index", kwargs=dict(year=year)))

        for c in Camp.objects.filter(year=year):
            self.assertContains(resp, c.get_absolute_url())


class DetailPage(BasicSetupMixin, TestBase):
    def test_get(self):
        camp = factories.create_camp(leader=factories.create_person(name=(leader_name := "Joe Bloggs")))
        resp = self.client.get(reverse("cciw-cciwmain-camps_detail", kwargs=dict(year=camp.year, slug=camp.slug_name)))
        self.assertContains(resp, leader_name)
        self.assertContains(resp, camp.camp_name.name)
