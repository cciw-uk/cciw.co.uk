from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache

from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp, CampName, Person, Site
from cciw.sitecontent.models import HtmlChunk, MenuLink
from cciw.utils.tests.base import FactoriesBase


class Factories(FactoriesBase):
    def __init__(self):
        # {year: [camp list]}
        self._camp_cache = defaultdict(list)

    def create_camp(
        self,
        *,
        start_date=None,
        end_date=None,
        site=None,
        camp_name=None,
        minimum_age=None,
        maximum_age=None,
        year=None,
        leader=None,
        leaders=None,
        chaplain=None,
        future=None,
        officers=None,
    ) -> Camp:
        assert not (leader is not None and leaders is not None), "Only supply one of 'leaders' and 'leader'"
        if leader:
            if leader is True:
                from cciw.officers.tests.base import factories as officers_factories

                leader = officers_factories.create_leader()
            leaders = [leader]
        elif not leaders:
            leaders = []

        if future is not None:
            assert start_date is None and end_date is None and year is None

        if start_date is None:
            if end_date is not None:
                start_date = end_date - timedelta(days=7)
            else:
                if year is not None:
                    # Some date in the summer
                    start_date = date(year, 8, 1)
                else:
                    if future:
                        start_date = date.today() + timedelta(days=365)
                    else:
                        start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        site = site or self.get_any_site()
        if minimum_age is None:
            if maximum_age is not None:
                minimum_age = maximum_age - 6
            else:
                minimum_age = 11
        if maximum_age is None:
            maximum_age = minimum_age + 6
        if year is not None:
            assert year == start_date.year
        else:
            year = start_date.year

        if isinstance(camp_name, str):
            camp_name = self.get_or_create_camp_name(camp_name)
        elif camp_name is None:
            camp_name = self._get_non_clashing_camp_name(year)

        camp = Camp.objects.create(
            end_date=end_date,
            camp_name=camp_name,
            site=site,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            year=year,
            start_date=start_date,
            chaplain=self.make_into_person(chaplain) if chaplain else None,
        )
        if leaders:
            self.set_camp_leaders(camp, leaders)
        if officers:
            from cciw.officers.tests.base import factories as officers_factories

            officers_factories.add_officers_to_camp(camp, officers)
        self._camp_cache[year].append(camp)
        return camp

    def _get_non_clashing_camp_name(self, year):
        # We have a unique constraint on name/year that we
        # need to respect to be able to create new camps.
        years_camps = self._camp_cache[year]
        name = self._get_next_camp_name(excluding=[camp.camp_name.name for camp in years_camps])
        return self.get_or_create_camp_name(name)

    def _get_next_camp_name(self, excluding=None) -> str:
        available_names = set(COLORS.keys())
        if excluding:
            available_names -= set(excluding)
        return sorted(available_names)[0]

    @lru_cache
    def get_any_camp(self):
        camp = Camp.objects.order_by("id").first()
        if camp is not None:
            return camp
        return self.create_camp()

    def create_camp_name(self, name=None, color=None):
        name = name or self._get_next_camp_name()
        color = color or COLORS.get(name, "#ff0000")
        camp_name = CampName.objects.create(
            name=name,
            slug=name.lower().replace(" ", "-"),
            color=color,
        )
        return camp_name

    @lru_cache
    def get_any_camp_name(self):
        camp_name = CampName.objects.order_by("id").first()
        if camp_name is not None:
            return camp_name
        return self.create_camp_name()

    @lru_cache
    def get_or_create_camp_name(self, name):
        try:
            return CampName.objects.get(name=name)
        except CampName.DoesNotExist:
            return self.create_camp_name(name=name)

    def create_site(self):
        return Site.objects.create(
            short_name="The Farm",
            long_name="The Farm in the Valley",
            slug_name="the-farm",
            info="A really lovely farm.",
        )

    @lru_cache
    def get_any_site(self):
        site = Site.objects.order_by("id").first()
        if site is not None:
            return site
        return self.create_site()

    def set_camp_leaders(self, camp, leaders):
        camp.leaders.set([self.make_into_person(leader) for leader in leaders])

    @lru_cache
    def get_any_camp_leader(self) -> Person:
        from cciw.officers.tests.base import factories as officer_factories

        person = Person.objects.first()
        if not person:
            user = officer_factories.get_any_officer()
            person = self.make_into_person(user)
        return person

    def make_into_person(self, user_or_person) -> Person:
        if isinstance(user_or_person, User):
            user = user_or_person
            person = self.create_person(name=user.full_name)
            person.users.set([user])
            return person
        elif isinstance(user_or_person, Person):
            return user_or_person
        else:
            raise NotImplementedError(f"Don't know what to do with {user_or_person}")

    def create_person(self, name=None) -> Person:
        return Person.objects.create(
            name=name,
        )

    def create_leaders(self, camp):
        leader_1 = Person.objects.create(name="Mr Leader")
        leader_2 = Person.objects.create(name="Mrs Leaderess")

        leader_1_user = User.objects.create(username="leader1", email="leader1@mail.com")
        leader_2_user = User.objects.create(username="leader2", email="leader2@mail.com")

        leader_1.users.add(leader_1_user)
        leader_2.users.add(leader_2_user)

        camp.leaders.add(leader_1)
        camp.leaders.add(leader_2)
        return (leader_1, leader_1_user), (leader_2, leader_2_user)


class SiteSetupMixin:
    def setUp(self):
        super().setUp()
        DjangoSite.objects.all().delete()
        DjangoSite.objects.create(domain=settings.PRODUCTION_DOMAIN, name=settings.PRODUCTION_DOMAIN, id=1)


class BasicSetupMixin(SiteSetupMixin):
    def setUp(self):
        super().setUp()

        m = MenuLink.objects.create(visible=True, extra_title="", parent_item=None, title="Home", url="/", listorder=0)

        HtmlChunk.objects.create(
            menu_link=m,
            html="<p>CCiW is a charitable company...</p>",
            page_title="Christian Camps in Wales",
            name="home_page",
        )

        HtmlChunk.objects.create(
            pk="booking_secretary_address",
            menu_link=None,
            html="<p>Booking Secretary,<br/>\r\n      James Bloggs,<br/>\r\n      12 Main Street",
            page_title="",
        )
        HtmlChunk.objects.create(name="bookingform_post_to", menu_link=None)

        self.default_site = Site.objects.create(
            info="Lots of info about this camp site, including: <address>Llys Andreas Camp Site, Wales</address>",
            long_name="Llys Andreas, Barmouth",
            slug_name="llys-andreas",
            short_name="Llys Andreas",
        )

        self.default_leader = Person.objects.create(
            info="Kevin and Tracey are members of Generic Baptist Church, London.  Kevin has been a leader or assistant leader on many camps (EMW, CCiW and church camps).",
            name="Kevin & Tracey Smith",
        )

        camp_name = factories.get_or_create_camp_name("Blue")

        self.default_camp_1 = factories.create_camp(
            camp_name=camp_name,
            site=self.default_site,
            start_date=date(2000, 7, 1),
        )
        self.default_camp_1.leaders.set([self.default_leader])

        self.default_camp_2 = factories.create_camp(
            camp_name=camp_name,
            site=self.default_site,
            start_date=date(2001, 7, 1),
        )
        self.default_camp_2.leaders.set([self.default_leader])


factories = Factories()


# Large list of names/colors we can use for creating CampName, especially for
# cases where we create lots of camps for performance testing.
COLORS = {
    "Red": "#FF0000",
    "Aero": "#7CB9E8",
    "Alabaster": "#EDEAE0",
    "Almond": "#EFDECD",
    "Amaranth": "#E52B50",
    "Amazon": "#3B7A57",
    "Amber": "#FFBF00",
    "Amethyst": "#9966CC",
    "Apricot": "#FBCEB1",
    "Aqua": "#00FFFF",
    "Aquamarine": "#7FFFD4",
    "Artichoke": "#8F9779",
    "Asparagus": "#87A96B",
    "Auburn": "#A52A2A",
    "Aureolin": "#FDEE00",
    "Avocado": "#568203",
    "Azure": "#007FFF",
    "Beaver": "#9F8170",
    "Beige": "#F5F5DC",
    "Bisque": "#FFE4C4",
    "Bistre": "#3D2B1F",
    "Bittersweet": "#FE6F5E",
    "Black": "#000000",
    "Blond": "#FAF0BE",
    "Blue": "#0000FF",
    "Bluetiful": "#3C69E7",
    "Blush": "#DE5D83",
    "Bole": "#79443B",
    "Bone": "#E3DAC9",
    "Brandy": "#87413F",
    "Bronze": "#CD7F32",
    "Brown": "#88540B",
    "Buff": "#FFC680",
    "Burgundy": "#800020",
    "Burlywood": "#DEB887",
    "Byzantine": "#BD33A4",
    "Byzantium": "#702963",
    "Cadet": "#536872",
    "Camel": "#C19A6B",
    "Canary": "#FFFF99",
    "Capri": "#00BFFF",
    "Cardinal": "#C41E3A",
    "Carmine": "#960018",
    "Carnelian": "#B31B1B",
    "Catawba": "#703642",
    "Celadon": "#ACE1AF",
    "Celeste": "#B2FFFF",
    "Cerise": "#DE3163",
    "Cerulean": "#007BA7",
    "Champagne": "#F7E7CE",
    "Charcoal": "#36454F",
    "Chestnut": "#954535",
    "Cinereous": "#98817B",
    "Cinnabar": "#E34234",
    "Citrine": "#E4D00A",
    "Citron": "#9FA91F",
    "Claret": "#7F1734",
    "Coffee": "#6F4E37",
    "Copper": "#B87333",
    "Coquelicot": "#FF3800",
    "Coral": "#FF7F50",
    "Cordovan": "#893F45",
    "Corn": "#FBEC5D",
    "Cornsilk": "#FFF8DC",
    "Cream": "#FFFDD0",
    "Crimson": "#DC143C",
    "Crystal": "#A7D8DE",
    "Cultured": "#F5F5F5",
    "Cyan": "#00FFFF",
    "Cyclamen": "#F56FA1",
    "Denim": "#1560BD",
    "Desert": "#C19A6B",
    "Drab": "#967117",
    "Ebony": "#555D50",
    "Ecru": "#C2B280",
    "Eggplant": "#614051",
    "Eggshell": "#F0EAD6",
    "Eigengrau": "#16161D",
    "Emerald": "#50C878",
    "Eminence": "#6C3082",
    "Erin": "#00FF40",
    "Fallow": "#C19A6B",
    "Fandango": "#B53389",
    "Fawn": "#E5AA70",
    "Feldgrau": "#4D5D53",
    "Firebrick": "#B22222",
    "Flame": "#E25822",
    "Flax": "#EEDC82",
    "Flirt": "#A2006D",
    "Frostbite": "#E936A7",
    "Fuchsia": "#FF00FF",
    "Fulvous": "#E48400",
}
