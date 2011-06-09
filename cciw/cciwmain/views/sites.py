from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from cciw.cciwmain.common import DefaultMetaData
from cciw.cciwmain.models import Site

class SiteList(DefaultMetaData, ListView):
    metadata_title = "Camp sites"
    template_name='cciw/sites/index.html'
    queryset = Site.objects.all()

index = SiteList.as_view()

class SiteDetail(DefaultMetaData, DetailView):
    queryset = Site.objects.all()
    slug_field = 'slug_name'
    template_name = 'cciw/sites/detail.html'

detail = SiteDetail.as_view()
