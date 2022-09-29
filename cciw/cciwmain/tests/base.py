from datetime import date

from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite

from cciw.cciwmain.models import Person, Site
from cciw.sitecontent.models import HtmlChunk, MenuLink

from . import factories

# TODO - a lot of this stuff should be rewritten as per https://gitlab.com/cciw/cciw.co.uk/-/issues/6
# especially removal of `default_site`, `default_camp_1` etc


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

        # A lot of this stuff below should be removed as per https://gitlab.com/cciw/cciw.co.uk/-/issues/6
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
