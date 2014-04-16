from cciw.cciwmain.common import CciwBaseView, DetailView, ListView
from cciw.cciwmain.models import Site

class SiteList(ListView, CciwBaseView):
    metadata_title = "Camp sites"
    template_name = 'cciw/sites/index.html'
    queryset = Site.objects.all()
    list_name = 'sites'

index = SiteList.as_view()


class SiteDetail(DetailView, CciwBaseView):
    queryset = Site.objects.all()
    slug_field = 'slug_name'
    object_name = 'site'
    template_name = 'cciw/sites/detail.html'

detail = SiteDetail.as_view()
