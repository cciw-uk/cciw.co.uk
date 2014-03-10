from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required

from cciw.officers.views import camp_admin_required
from cciw.mail.lists import list_for_address

@staff_member_required
@camp_admin_required
def show_list(request, address):
    emails = list_for_address(address)
    if emails is None:
        return HttpResponse("No such list '{}'".format(address), status=404)
    return HttpResponse(u",\n".join(emails),
                        content_type="text/plain")
