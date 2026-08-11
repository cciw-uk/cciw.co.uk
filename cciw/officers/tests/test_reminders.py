from datetime import date, timedelta

from django.core import mail
from django.test import Client
from django.urls import reverse
from time_machine import travel

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.email import send_data_retention_reminder_emails
from cciw.officers.tests import factories as officer_factories
from cciw.officers.views.leaders.officer_list import officer_data_filename


def test_data_cleanup_reminders(db, client: Client):
    with travel(date(2021, 1, 2)):
        leader = officer_factories.create_officer()
        admin_user = officer_factories.create_officer()
        other_user = officer_factories.create_officer()
        camp = camp_factories.create_camp(leader=leader, start_date=date(2021, 8, 1))
        officer_factories.add_officers_to_camp(camp, [leader, admin_user, other_user])
        camp.admins.add(admin_user)

        # The leader downloaded some data:
        download_officer_data(client, user=leader, camp=camp)

    with travel(date(2022, 1, 2)):
        # Another camp is created for 2022
        later_camp = camp_factories.create_camp(leader=leader, start_date=date(2022, 8, 1))

    admin_user_count = len([admin_user, leader])

    # Leader should get reminder about deleting officer data
    # one year after the end of camp. Wait of one month after the last camp
    # from this, see comments in send_data_retention_reminder_emails

    mail.outbox = []
    with travel(later_camp.end_date + timedelta(days=35)):
        send_data_retention_reminder_emails()
        assert len(mail.outbox) == admin_user_count
        m = mail.outbox[0]
        assert m.subject == f"[CCIW] Reminder: remove officer data for {camp.name} Camp, year 2021"
        assert camp.nice_name in m.body

        leader_mail = [m for m in mail.outbox if m.to == [leader.email]][0]
        # This should have download logs in it
        expected_file_name = f"{officer_data_filename(camp)}.xlsx"
        assert expected_file_name in leader_mail.body

    # No further emails when checking later.
    with travel(later_camp.end_date + timedelta(days=36)):
        send_data_retention_reminder_emails()
        assert len(mail.outbox) == admin_user_count


def download_officer_data(client: Client, user: User, camp: Camp) -> None:
    client.force_login(user)
    url1 = (
        reverse("cciw-officers-export_officer_data", kwargs=dict(camp_id=camp.url_id)) + "?data_retention_notice_seen=1"
    )
    client.get(url1)
