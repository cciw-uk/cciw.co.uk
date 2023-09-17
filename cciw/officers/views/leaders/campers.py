from django.contrib.admin.views.decorators import staff_member_required

from cciw.bookings.utils import (
    camp_bookings_to_spreadsheet,
    camp_sharable_transport_details_to_spreadsheet,
)
from cciw.cciwmain.common import CampId

from ..utils.auth import (
    camp_admin_required,
)
from ..utils.campid import get_camp_or_404
from ..utils.data_retention import DataRetentionNotice, show_data_retention_notice
from ..utils.spreadsheets import spreadsheet_response


@staff_member_required
@camp_admin_required
@show_data_retention_notice(DataRetentionNotice.CAMPERS, "Camper data")
def export_camper_data(request, camp_id: CampId):
    camp = get_camp_or_404(camp_id)
    return spreadsheet_response(
        camp_bookings_to_spreadsheet(camp),
        f"CCIW-camp-{camp.url_id}-campers",
        notice=DataRetentionNotice.CAMPERS,
    )


@staff_member_required
@camp_admin_required
@show_data_retention_notice(DataRetentionNotice.CAMPERS, "Camper sharable transport details")
def export_sharable_transport_details(request, camp_id: CampId):
    camp = get_camp_or_404(camp_id)
    return spreadsheet_response(
        camp_sharable_transport_details_to_spreadsheet(camp),
        f"CCIW-camp-{camp.url_id}-transport-details",
        notice=DataRetentionNotice.CAMPERS,
    )
