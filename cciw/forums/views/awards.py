from cciw.cciwmain.common import CciwBaseView, ListView

from cciw.forums.models import Award


class AwardList(ListView, CciwBaseView):
    metadata_title = "Website Awards"
    template_name = "cciw/awards/index.html"
    queryset = Award.objects.order_by('-year', '-value')
    list_name = 'awards'

index = AwardList.as_view()
