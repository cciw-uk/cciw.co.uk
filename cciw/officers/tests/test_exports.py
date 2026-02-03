from django.test import Client
from django.urls import reverse

from cciw.bookings import factories
from cciw.bookings.models.queue import allocate_bookings_now
from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.tests import factories as officer_factories


def test_export_camper_data(db, client: Client):
    user = officer_factories.create_officer()
    camp = camp_factories.create_camp(leader=user)
    booking = factories.create_booking(camp=camp)
    allocate_bookings_now([booking])

    client.force_login(user)
    url1 = reverse("cciw-officers-export_camper_data", kwargs=dict(camp_id=camp.url_id))
    resp1 = client.get(url1)

    # We get data retention notice first of all
    assert resp1.headers["Content-Type"] == "text/html; charset=utf-8"

    # Clicking the link:
    assert b"Camper information data retention" in resp1.content
    url2 = url1 + "?data_retention_notice_seen=1"
    resp2 = client.get(url2)

    assert resp2.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert (
        resp2.headers["Content-Disposition"]
        == f"attachment; filename=CCIW-camp-{camp.year}-{camp.slug_name}-campers.xlsx"
    )
    # Content is tested more easily using tests for `camp_bookings_to_spreadsheet`
