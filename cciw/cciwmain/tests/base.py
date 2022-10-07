from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite


class SiteSetupMixin:
    def setUp(self):
        super().setUp()
        DjangoSite.objects.all().delete()
        DjangoSite.objects.create(domain=settings.PRODUCTION_DOMAIN, name=settings.PRODUCTION_DOMAIN, id=1)
