import pytest
from django.urls import reverse

from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests.utils import FuzzyInt, init_query_caches
from cciw.sitecontent.models import HtmlChunk
from cciw.test_utils.base import TestBase

from . import factories

pytestmark = pytest.mark.django_db


def test_camp_names():
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


def test_camp_previous_and_next():
    camp_1 = factories.create_camp(year=2013, camp_name="Blue")
    camp_2 = factories.create_camp(year=2014, camp_name="Blue")

    camp_3 = factories.create_camp(year=2016, camp_name="Blue")

    assert camp_1.next_camp == camp_2
    assert camp_1.previous_camp is None
    assert camp_2.previous_camp == camp_1

    # If there is a gap, we consider the chain broken. This is
    # helpful for cases like Blue camp in 2026 which was a completely
    # "different" camp from earlier camps.

    assert camp_3.previous_camp is None
    assert camp_2.next_camp is None
    assert camp_3.next_camp is None

    # This logic is less helpful for cases where camps may be forced
    # to take a break because of circumstances like COVID 19.
    # However:
    #  - the previous/next link is not used in that many cases,
    #
    #  - the link is never really needed for historic cases. i.e. we don't
    #    really care whether we correctly determine that purple-2022 is next
    #    camp of purple-2019, but we do care whether this year's camp is
    #    connected to previous year's camp, or not, correctly.
    #
    #  - if something similar comes up again, we can think how to handle it.
    #    Maybe we need explicit 'previous' FKs, but this
    #    is more work to handle.

    camp_dict = {c.id: c for c in [camp_1, camp_2, camp_3]}

    # Test prefetch branch code:
    camps = Camp.objects.select_related("camp_name").prefetch_related("camp_name__camps")
    for camp in camps:
        matching_camp = camp_dict[camp.id]
        assert camp.next_camp == matching_camp.next_camp
        assert camp.previous_camp == matching_camp.previous_camp


class ThisyearPage(TestBase):
    def setUp(self):
        super().setUp()
        HtmlChunk.objects.create(name="camp_dates_intro_text")
        HtmlChunk.objects.create(name="camp_dates_outro_text")

    def test_get(self):
        init_query_caches()
        for i in range(0, 20):
            factories.create_camp(leader=factories.get_any_camp_leader(), future=True)
        with self.assertNumQueries(FuzzyInt(1, 8)):
            resp = self.client.get(reverse("cciw-cciwmain-thisyear"))

        for c in Camp.objects.all():
            self.assertContains(resp, c.get_absolute_url())


class IndexPage(TestBase):
    def test_get(self):
        init_query_caches()
        year = 2020
        for i in range(0, 20):
            factories.create_camp(year=year, leader=factories.get_any_camp_leader())

        with self.assertNumQueries(FuzzyInt(1, 6)):
            resp = self.client.get(reverse("cciw-cciwmain-camps_year_index", kwargs=dict(year=year)))

        for c in Camp.objects.filter(year=year):
            self.assertContains(resp, c.get_absolute_url())


class DetailPage(TestBase):
    def test_get(self):
        camp = factories.create_camp(leader=factories.create_person(name=(leader_name := "Joe Bloggs")))
        resp = self.client.get(reverse("cciw-cciwmain-camps_detail", kwargs=dict(year=camp.year, slug=camp.slug_name)))
        self.assertContains(resp, leader_name)
        self.assertContains(resp, camp.camp_name.name)
