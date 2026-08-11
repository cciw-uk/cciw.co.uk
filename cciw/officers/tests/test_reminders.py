from collections.abc import Iterable, Sequence
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
from cciw.officers.views.leaders.officer_list import officer_data_filename_stem


def test_data_cleanup_reminders(db, client: Client):
    with travel(date(2021, 1, 2)):
        leader = officer_factories.create_officer()
        admin_user = officer_factories.create_officer()
        other_user = officer_factories.create_officer()  # shouldn't be emailed
        # Simulate a user who was added as an admin,
        # and then removed, so was able to download stuff
        temp_admin = officer_factories.create_officer()
        camp = camp_factories.create_camp(leader=leader, start_date=date(2021, 8, 1))
        officer_factories.add_officers_to_camp(camp, [leader, admin_user, other_user])
        camp.admins.add(admin_user)
        camp.admins.add(temp_admin)

        downloading_users = [leader, temp_admin]
        for user in downloading_users:
            download_officer_data(client, user=user, camp=camp)

        # temp_admin is removed.
        camp.admins.remove(temp_admin)

    with travel(date(2022, 1, 2)):
        # Another camp is created for 2022
        # (just for more realistic data)
        later_camp = camp_factories.create_camp(leader=leader, start_date=date(2022, 8, 1))

    admin_users = [leader, admin_user, temp_admin]
    admin_user_count = len(admin_users)

    # Leader should get reminder about deleting officer data one year after the
    # end of camp. We wait at least one month after the last camp from this
    # date, see comments in send_data_retention_reminder_emails

    mail.outbox = []
    with travel(later_camp.end_date + timedelta(days=35)):
        send_data_retention_reminder_emails()
        assert len(mail.outbox) == admin_user_count
        for m, user in sort_emails_by_user(mail.outbox, admin_users):
            assert m.subject == f"[CCIW] Reminder: remove officer data for {camp.name} Camp, year 2021"
            assert camp.nice_name in m.body

            expected_file_name = f"{officer_data_filename_stem(camp)}.xlsx"
            if user in downloading_users:
                # Should have download logs in it
                assert expected_file_name in m.body
            else:
                assert expected_file_name not in m.body

    # No further emails when checking later.
    with travel(later_camp.end_date + timedelta(days=36)):
        send_data_retention_reminder_emails()
        assert len(mail.outbox) == admin_user_count


def sort_emails_by_user(
    mails: Sequence[mail.EmailMessage], users: Sequence[User]
) -> Iterable[tuple[mail.EmailMessage, User]]:
    d = {user.email: user for user in users}
    assert len(d) == len(users)
    for m in mails:
        yield m, d[m.to[0]]


def download_officer_data(client: Client, user: User, camp: Camp) -> None:
    client.force_login(user)
    url1 = (
        reverse("cciw-officers-export_officer_data", kwargs=dict(camp_id=camp.url_id)) + "?data_retention_notice_seen=1"
    )
    client.get(url1)
