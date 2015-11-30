from datetime import date

from django.contrib.sites.models import Site as DjangoSite

from cciw.cciwmain.models import Site, Camp, Person, CampName
from cciw.sitecontent.models import MenuLink, HtmlChunk


class BasicSetupMixin(object):
    def setUp(self):
        super(BasicSetupMixin, self).setUp()
        DjangoSite.objects.all().delete()
        DjangoSite.objects.create(
            domain="www.cciw.co.uk",
            name="www.cciw.co.uk",
            id=1)

        MenuLink.objects.create(
            visible=True,
            extra_title="",
            parent_item=None,
            title="Home",
            url="/",
            listorder=0)

        HtmlChunk.objects.create(
            pk="booking_secretary_address",
            menu_link=None,
            html="<p>Booking Secretary,<br/>\r\n      James Bloggs,<br/>\r\n      12 Main Street",
            page_title="")

        self.default_site = Site.objects.create(
            info="Lots of info about this camp site, including: <address>Llys Andreas Camp Site, Wales</address>",
            long_name="Llys Andreas, Barmouth",
            slug_name="llys-andreas",
            short_name="Llys Andreas")

        self.default_leader = Person.objects.create(
            info="Dave and Rebecca are members of Grace Baptist Church, Southport.  Dave has been a leader or assistant leader on many camps (EMW, CCIW and church camps).",
            name="Dave & Rebecca Stott")

        camp_name = CampName.objects.create(
            name="Blue",
            slug="blue",
        )

        self.default_camp_1 = Camp.objects.create(
            end_date=date(2000, 7, 8),
            number=1,
            camp_name=camp_name,
            site=self.default_site,
            minimum_age=11,
            maximum_age=17,
            year=2000,
            start_date=date(2000, 7, 1),
            chaplain=None)
        self.default_camp_1.leaders = [self.default_leader]

        self.default_camp_2 = Camp.objects.create(
            previous_camp=self.default_camp_1,
            end_date=date(2001, 7, 8),
            number=1,
            camp_name=camp_name,
            site=self.default_site,
            minimum_age=11,
            maximum_age=17,
            year=2001,
            start_date=date(2001, 7, 1),
            chaplain=None)
        self.default_camp_2.leaders = [self.default_leader]
