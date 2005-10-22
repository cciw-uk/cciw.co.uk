from django.models.members import awards
from django.views.generic import list_detail
from cciw.apps.cciw.common import *

def index(request):
    return list_detail.object_list(request, app_label = 'members', module_name = 'awards',
        extra_context = standard_extra_context(request, title="Website Awards"),
        template_name = 'cciw/awards/index')
