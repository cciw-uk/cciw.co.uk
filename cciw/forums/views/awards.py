from django.views.generic.list import ListView
from cciw.cciwmain.common import DefaultMetaData

from cciw.forums.models import Award

class AwardList(DefaultMetaData, ListView):
    metadata_title = "Website Awards"
    template_name = "cciw/awards/index.html"
    queryset = Award.objects.order_by('-year', '-value')

index = AwardList.as_view()
