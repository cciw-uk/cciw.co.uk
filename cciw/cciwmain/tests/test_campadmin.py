from datetime import timedelta

from django.urls import reverse

from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.tests import factories as officer_factories
from cciw.utils.tests.webtest import WebTestBase


class CampAdmin(WebTestBase):
    def test_officer_cant_edit_camp(self):
        camp = camp_factories.create_camp()
        self.officer_login(officer_factories.create_officer())

        self.get_literal_url(reverse("admin:cciwmain_camp_changelist"), expect_errors=True)
        self.assertCode(403)
        self.get_literal_url(reverse("admin:cciwmain_camp_change", args=(camp.id,)), expect_errors=True)
        self.assertCode(403)

    def test_leaders_can_edit_current_camp(self):
        camp = camp_factories.create_camp(leader=(leader := officer_factories.create_officer()))
        old_camp = camp_factories.create_camp(leader=leader, year=camp.year - 1)
        other_camp = camp_factories.create_camp()
        self.officer_login(leader)
        self.get_url("admin:cciwmain_camp_changelist")
        assert camp in leader.camps_as_admin_or_leader
        assert other_camp not in leader.camps_as_admin_or_leader
        assert self.is_element_present(f'[href="/admin/cciwmain/camp/{camp.id}/change/"]')
        assert not self.is_element_present(f'[href="/admin/cciwmain/camp/{other_camp.id}/change/"]')
        self.follow_link(f'[href="/admin/cciwmain/camp/{camp.id}/change/"]')

        # Camp leaders can change last_booking_date
        self.fill(
            {"#id_last_booking_date": (last_booking_date := camp.end_date - timedelta(days=1)).strftime("%Y-%m-%d")}
        )

        # But camp leaders can't change booking limits
        assert not self.is_element_present("#id_max_campers")

        self.submit('[name="_save"]')
        camp.refresh_from_db()
        assert camp.last_booking_date == last_booking_date

        # Old camp is not editable:
        self.get_url("admin:cciwmain_camp_change", old_camp.id)
        assert not self.is_element_present('[name="_save"]')
