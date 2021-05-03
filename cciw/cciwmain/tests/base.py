from datetime import date, timedelta

from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp, CampName, Person, Site
from cciw.sitecontent.models import HtmlChunk, MenuLink


class Factories:
    def create_camp(
            self, *,
            start_date=None,
            end_date=None,
            site=None,
            camp_name=None,
            minimum_age=None,
            maximum_age=None,
            year=None,
            leader=None,
    ):
        requested_camp_name = camp_name
        if isinstance(camp_name, str):
            camp_name = self.get_or_create_camp_name(camp_name)
        elif camp_name is None:
            camp_name = self.get_any_camp_name()
        if start_date is None:
            if end_date is not None:
                start_date = end_date - timedelta(days=7)
            else:
                if year is not None:
                    # Some date in the summer
                    start_date = date(year, 8, 1)
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
        if Camp.objects.filter(
                camp_name=camp_name,
                year=year
        ).exists() and requested_camp_name is None:
            # Hack, need a better way to do this.
            # This only works for 2 camps.
            camp_name = self.create_camp_name(name='other')

        camp = Camp.objects.create(
            end_date=end_date,
            camp_name=camp_name,
            site=site,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            year=year,
            start_date=start_date,
            chaplain=None,
        )
        if leader is not None:
            self.set_camp_leader(camp, leader)
        return camp

    def get_any_camp(self):
        # TODO - a way to cache values - needs to work well with DB - i.e.
        # should be flushed after each test is run, because otherwise
        # the cached object won't exist in the DB.

        # Also for other get_any_ below
        camp = Camp.objects.order_by('id').first()
        if camp is not None:
            return camp
        return self.create_camp()

    def create_camp_name(self, name=None):
        name = name or 'Violet'
        camp_name = CampName.objects.create(
            name=name,
            slug=name.lower().replace(' ', '-'),
            color='#ff0000',
        )
        return camp_name

    def get_any_camp_name(self):
        camp_name = CampName.objects.order_by('id').first()
        if camp_name is not None:
            return camp_name
        return self.create_camp_name()

    def get_or_create_camp_name(self, name):
        try:
            return CampName.objects.get(name=name)
        except CampName.DoesNotExist:
            return self.create_camp_name(name=name)

    def create_site(self):
        return Site.objects.create(
            short_name='The Farm',
            long_name='The Farm in the Valley',
            slug_name='the-farm',
            info='A really lovely farm.'
        )

    def get_any_site(self):
        site = Site.objects.order_by('id').first()
        if site is not None:
            return site
        return self.create_site()

    def set_camp_leader(self, camp, leader):
        if isinstance(leader, User):
            leader_person = Person.objects.create(
                name=leader.full_name
            )
            leader_person.users.set([leader])
            camp.leaders.set([leader_person])
        else:
            raise NotImplementedError(f"Don't know what to do with {leader}")


class BasicSetupMixin(object):
    def setUp(self):
        super().setUp()
        DjangoSite.objects.all().delete()
        DjangoSite.objects.create(
            domain=settings.PRODUCTION_DOMAIN,
            name=settings.PRODUCTION_DOMAIN,
            id=1)

        m = MenuLink.objects.create(
            visible=True,
            extra_title="",
            parent_item=None,
            title="Home",
            url="/",
            listorder=0)

        HtmlChunk.objects.create(
            menu_link=m,
            html="<p>CCiW is a charitable company...</p>",
            page_title="Christian Camps in Wales",
            name='home_page',
        )

        HtmlChunk.objects.create(
            pk="booking_secretary_address",
            menu_link=None,
            html="<p>Booking Secretary,<br/>\r\n      James Bloggs,<br/>\r\n      12 Main Street",
            page_title="")
        HtmlChunk.objects.create(name="bookingform_post_to", menu_link=None)

        self.default_site = Site.objects.create(
            info="Lots of info about this camp site, including: <address>Llys Andreas Camp Site, Wales</address>",
            long_name="Llys Andreas, Barmouth",
            slug_name="llys-andreas",
            short_name="Llys Andreas")

        self.default_leader = Person.objects.create(
            info="Kevin and Tracey are members of Generic Baptist Church, London.  Kevin has been a leader or assistant leader on many camps (EMW, CCiW and church camps).",
            name="Kevin & Tracey Smith")

        camp_name, _ = CampName.objects.get_or_create(
            name="Blue",
            slug="blue",
            color="#0000ff",
        )

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
