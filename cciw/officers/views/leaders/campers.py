from django.http import HttpRequest

from cciw.bookings.utils import (
    camp_bookings_to_spreadsheet,
    camp_sharable_transport_details_to_spreadsheet,
)
from cciw.cciwmain.common import CampId

from ...models.data_retention import DataRelatedToCampersOnCamp
from ..utils.auth import (
    camp_admin_required,
)
from ..utils.campid import get_camp_or_404
from ..utils.data_retention import (
    DataRetentionNotice,
    SensitiveDownloadResponse,
    sensitive_data_download,
)
from ..utils.spreadsheets import spreadsheet_response


@camp_admin_required
@sensitive_data_download(DataRetentionNotice.CAMPERS, "Camper data")
def export_camper_data(request: HttpRequest, camp_id: CampId) -> SensitiveDownloadResponse:
    camp = get_camp_or_404(camp_id)
    return spreadsheet_response(
        camp_bookings_to_spreadsheet(camp),
        f"CCIW-camp-{camp.url_id}-campers",
        notice=DataRetentionNotice.CAMPERS,
        data_relation=DataRelatedToCampersOnCamp(camp=camp),
    )


@camp_admin_required
@sensitive_data_download(DataRetentionNotice.CAMPERS, "Camper sharable transport details")
def export_sharable_transport_details(request: HttpRequest, camp_id: CampId) -> SensitiveDownloadResponse:
    camp = get_camp_or_404(camp_id)
    return spreadsheet_response(
        camp_sharable_transport_details_to_spreadsheet(camp),
        f"CCIW-camp-{camp.url_id}-transport-details",
        notice=DataRetentionNotice.CAMPERS,
        data_relation=DataRelatedToCampersOnCamp(camp=camp),
    )
