from django.shortcuts import get_object_or_404

from cciw.cciwmain.common import CciwBaseView
from cciw.cciwmain.models import Site


class SiteList(CciwBaseView):
    metadata_title = "Camp sites"
    template_name = 'cciw/sites/index.html'

    def handle(self, request):
        return self.render({'sites': Site.objects.all()})


class SiteDetail(CciwBaseView):
    template_name = 'cciw/sites/detail.html'

    def handle(self, request, slug=None):
        return self.render({'site': get_object_or_404(Site.objects.filter(slug_name=slug))})


index = SiteList.as_view()
detail = SiteDetail.as_view()
