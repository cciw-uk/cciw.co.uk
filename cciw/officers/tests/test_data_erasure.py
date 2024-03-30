from django_functest import FuncBaseMixin

from cciw.contact_us.models import Message
from cciw.contact_us.tests import create_message
from cciw.data_retention.models import ErasureExecutionLog
from cciw.officers.tests import factories
from cciw.utils.tests.webtest import WebTestBase


class DataErasureRequestTestsBase(FuncBaseMixin):
    def setUp(self):
        super().setUp()
        self.webmaster = factories.create_webmaster()
        self.shortcut_login(self.webmaster)

    def test_report_and_execute(self):
        officer = factories.create_officer(first_name="Joe", last_name="Bloggs", email="joe@example.com")
        application = factories.create_application(officer=officer)
        officer2 = factories.create_officer(first_name="Joan", last_name="Bloggs", email="joan@example.com")
        message = create_message(email="joe@example.com")
        self.get_url("cciw-officers-data_erasure_request_start")
        self.fill({"#searchbar": "joe@example.com"})

        self.submit("[type=submit]")
        self.assertTextPresent("Joe Bloggs")
        self.assertTextAbsent("Joan Bloggs")
        self.assertTextAbsent(officer2.email)

        self.fill(
            {
                # Use some internals here, ideally we'd loop over all checkbox inputs
                f'[value="accounts.User:{officer.id}"]': True,
                f'[value="officers.Application:{application.id}"]': True,
                f'[value="contact_us.Message:{message.id}"]': True,
            }
        )
        self.submit("[name=plan]")

        self.assertTextPresent("Data erasure request report")

        # account.User
        self.assertTextPresent("Record type:")
        self.assertTextPresent("accounts.User")
        self.assertTextPresent("User account for cciw.co.uk staff functions, especially camp officers")
        self.assertTextPresent("Erase columns from 1 `accounts.User` record(s)")

        self.assertTextPresent("The following columns will be erased:")
        self.assertTextPresent("password")

        # officers.Application
        self.assertTextPresent("officers.Application")
        self.assertTextPresent("Officer's application form, required to come on camp.")

        # contact_us.Message
        self.assertTextPresent("Delete 1 `contact_us.Message` record(s)")

        self.submit("[name=execute]")

        officer.refresh_from_db()
        assert officer.email == "joe@example.com"  # policy requires this to be kept
        assert officer.contact_phone_number == "[deleted]"
        application.refresh_from_db()
        assert application.address_email == "deleted@example.com"

        assert not Message.objects.filter(id=message.id).exists()

        log = ErasureExecutionLog.objects.last()
        assert log.plan_details == {
            "type": "ErasurePlan",
            "items": [
                {
                    "commands": [
                        {
                            "group": {"name": "Deleteable officer data"},
                            "records": [
                                {
                                    "model": "accounts.User",
                                    "pk": officer.id,
                                }
                            ],
                            "type": "UpdateCommand",
                            "update_dict": {
                                "keys": ["password", "contact_phone_number", "erased_at"],
                            },
                        }
                    ],
                    "result": {
                        "model": "accounts.User",
                        "pk": officer.id,
                        "type": "SearchResult",
                    },
                    "type": "ErasurePlanItem",
                },
                {
                    "commands": [
                        {
                            "group": {"name": "Deleteable officer data"},
                            "records": [
                                {
                                    "model": "officers.Application",
                                    "pk": application.id,
                                }
                            ],
                            "type": "UpdateCommand",
                            "update_dict": {
                                "keys": [
                                    "birth_date",
                                    "birth_place",
                                    "address_firstline",
                                    "address_town",
                                    "address_county",
                                    "address_postcode",
                                    "address_country",
                                    "address_tel",
                                    "address_mobile",
                                    "address_email",
                                    "erased_at",
                                ]
                            },
                        }
                    ],
                    "result": {
                        "model": "officers.Application",
                        "pk": application.id,
                        "type": "SearchResult",
                    },
                    "type": "ErasurePlanItem",
                },
                {
                    "commands": [
                        {
                            "group": {
                                "name": "Temporary data",
                            },
                            "records": [
                                {
                                    "model": "contact_us.Message",
                                    "pk": message.id,
                                },
                            ],
                            "type": "DeleteCommand",
                        },
                    ],
                    "result": {
                        "model": "contact_us.Message",
                        "pk": message.id,
                        "type": "SearchResult",
                    },
                    "type": "ErasurePlanItem",
                },
            ],
        }


class DataErasureRequestTestsWT(DataErasureRequestTestsBase, WebTestBase):
    pass
