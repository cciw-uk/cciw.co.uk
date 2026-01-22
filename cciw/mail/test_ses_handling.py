from unittest import mock

import pytest
from django.core import mail
from django.test.client import RequestFactory

from cciw.cciwmain.tests import factories as camp_factories
from cciw.officers.models import Referee, ReferenceAction
from cciw.officers.tests import factories as officer_factories

from . import views
from .test_data import AWS_BOUNCE_NOTIFICATION, AWS_MESSAGE_ID, AWS_SNS_NOTIFICATION

pytestmark = pytest.mark.django_db


def test_ses_incoming():
    request = make_plain_text_request("/", AWS_SNS_NOTIFICATION["body"], AWS_SNS_NOTIFICATION["headers"])
    with (
        mock.patch("cciw.aws.verify_sns_notification") as m1,
        mock.patch("cciw.mail.views.handle_mail_from_s3_async") as m2,
    ):
        m1.side_effect = [True]  # fake verify
        response = views.ses_incoming_notification(request)

    assert response.status_code == 200
    assert m1.call_count == 1
    assert m2.call_count == 1
    assert m2.call_args[0][0] == AWS_MESSAGE_ID.decode("ascii")


# TODO it would be nice to have tests for cciw/aws.py functions,
# to ensure no regressions.


def test_ses_bounce_for_reference():
    camp = camp_factories.create_camp(
        camp_name="Blue",
        year=2000,  # Matches X-CCIW-Camp header in AWS_BOUNCE_NOTIFICATION
    )
    officer = officer_factories.create_officer()
    officer_factories.add_officers_to_camp(camp, [officer])
    app = officer_factories.create_application(
        officer=officer,
        referee1_email="a.referrer@example.com",  # Match email in AWS_BOUNCE_NOTIFICATION
    )
    # Make it match AWS_BOUNCE_NOTIFICATION
    Referee.objects.filter(id=app.referees[0].id).update(id=1234)
    app.refresh_from_db()
    referee = app.referees[0]
    assert referee.id == 1234

    request = make_plain_text_request("/", AWS_BOUNCE_NOTIFICATION["body"], AWS_BOUNCE_NOTIFICATION["headers"])
    with mock.patch("cciw.aws.verify_sns_notification") as m1:
        m1.side_effect = [True]  # fake verify
        response = views.ses_bounce_notification(request)

    assert response.status_code == 200
    assert m1.call_count == 1

    assert len(mail.outbox) == 1
    m = mail.outbox[0]
    assert m.to == ["a.camp.leader@example.com"]
    assert "was not received" in m.body
    assert "sent to a.referrer@example.com" in m.body
    assert "Use the following link" in m.body
    assert response.status_code == 200

    actions = referee.actions.filter(action_type=ReferenceAction.ActionType.EMAIL_TO_REFEREE_BOUNCED)
    assert len(actions) == 1
    assert actions[0].bounced_email == "a.referrer@example.com"


def make_plain_text_request(path: str, body: str, headers: dict):
    mangled_headers = {"HTTP_" + name.replace("-", "_").upper(): value for name, value in headers.items()}
    return RequestFactory().generic(
        "POST", path, data=body, content_type="text/plain; charset=UTF-8", **mangled_headers
    )
