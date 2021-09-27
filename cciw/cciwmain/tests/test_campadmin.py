from django.urls import reverse

from cciw.cciwmain.models import Camp
from cciw.officers.tests.base import LEADER, OFFICER, CurrentCampsMixin, OfficersSetupMixin
from cciw.utils.tests.webtest import WebTestBase


class CampAdmin(CurrentCampsMixin, OfficersSetupMixin, WebTestBase):
    def test_officer_cant_edit_camp(self):
        self.officer_login(OFFICER)
        camp = Camp.objects.first()

        self.get_literal_url(reverse("admin:cciwmain_camp_changelist"), expect_errors=True)
        self.assertCode(403)
        self.get_literal_url(reverse("admin:cciwmain_camp_change", args=(camp.id,)), expect_errors=True)
        self.assertCode(403)

    def test_leaders_can_edit_current_camp(self):
        self.officer_login(LEADER)
        leader = self.leader_user
        (camp,) = leader.current_camps_as_admin_or_leader
        other_camps = Camp.objects.all().exclude(id=camp.id)
        self.get_url("admin:cciwmain_camp_changelist")
        for c in other_camps:
            if camp in leader.camps_as_admin_or_leader:
                assert self.is_element_present(f'[href="/admin/cciwmain/camp/{c.id}/change/"]')
            else:
                assert not self.is_element_present(f'[href="/admin/cciwmain/camp/{c.id}/change/"]')
        self.follow_link(f'[href="/admin/cciwmain/camp/{camp.id}/change/"]')
        self.fill({"#id_max_campers": 47})
        self.submit('[name="_save"]')
        assert camp.max_campers != 47
        camp.refresh_from_db()
        assert camp.max_campers == 47

        # Old camp is not editable:
        old_camp = leader.camps_as_admin_or_leader.exclude(id=camp.id).get()
        self.get_url("admin:cciwmain_camp_change", old_camp.id)
        assert not self.is_element_present('[name="_save"]')
