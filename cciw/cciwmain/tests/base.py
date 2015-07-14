from datetime import datetime

from django.contrib.sites.models import Site as DjangoSite
from django_dynamic_fixture import G

from cciw.cciwmain.models import Site, Camp, Person
from cciw.sitecontent.models import MenuLink, HtmlChunk


class BasicSetupMixin(object):
    def setUp(self):
        super(BasicSetupMixin, self).setUp()
        DjangoSite.objects.all().delete()
        G(DjangoSite,
          domain="www.cciw.co.uk",
          name="www.cciw.co.uk",
          id=1,
          )

        G(MenuLink,
          visible=True,
          extra_title="",
          parent_item=None,
          title="Home",
          url="/",
          listorder=0)

        G(HtmlChunk,
          pk="booking_secretary_address",
          menu_link=None,
          html="<p>Booking Secretary,<br/>\r\n      James Bloggs,<br/>\r\n      12 Main Street",
          page_title="")

        self.default_site = G(Site,
                              info="Site 1 info",
                              long_name="Site 1 long name",
                              slug_name="llys-andreas",
                              short_name="Site 1")

        self.default_leader = G(Person,
                                info="Dave and Rebecca are members of Grace Baptist Church, Southport.  Dave has been a leader or assistant leader on many camps (EMW, CCIW and church camps).",
                                name="Dave & Rebecca Stott")

        self.default_camp_1 = G(Camp,
                                end_date=datetime(2000, 7, 8),
                                online_applications=True,
                                number=1,
                                site=self.default_site,
                                minimum_age=11,
                                maximum_age=17,
                                year=2000,
                                start_date=datetime(2000, 7, 1),
                                leaders=[self.default_leader],
                                chaplain=None)

        self.default_camp_2 = G(Camp,
                                end_date=datetime(2001, 7, 8),
                                online_applications=True,
                                number=1,
                                site=self.default_site,
                                minimum_age=11,
                                maximum_age=17,
                                year=2001,
                                start_date=datetime(2001, 7, 1),
                                leaders=[self.default_leader],
                                chaplain=None)
