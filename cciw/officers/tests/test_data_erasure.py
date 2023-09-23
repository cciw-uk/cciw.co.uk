from django_functest import FuncBaseMixin

from cciw.officers.tests import factories
from cciw.utils.tests.webtest import WebTestBase


class DataErasureRequestTestsBase(FuncBaseMixin):
    def setUp(self):
        super().setUp()
        self.webmaster = factories.create_webmaster()
        self.shortcut_login(self.webmaster)

    def test_report(self):
        officer = factories.create_officer(first_name="Joe", last_name="Bloggs", email="joe@example.com")
        application = factories.create_application(officer=officer)
        officer2 = factories.create_officer(first_name="Joan", last_name="Bloggs", email="joan@example.com")
        self.get_url("cciw-officers-data_erasure_request_start")
        self.fill({"#searchbar": "joe@example.com"})

        self.submit("[type=submit]")
        self.assertTextPresent("Joe Bloggs")
        self.assertTextAbsent("Joan Bloggs")
        self.assertTextAbsent(officer2.email)

        # Getting inputs web UI programmatically is hard at the moment,
        # use some internals for generating selectors:

        self.fill(
            {
                f'[value="accounts.User:{officer.id}"]': True,
                f'[value="officers.Application:{application.id}"]': True,
            }
        )
        self.submit("[name=plan]")

        self.assertTextPresent("Data erasure request report")

        self.assertTextPresent("Record type:")
        self.assertTextPresent("accounts.User")
        self.assertTextPresent("User account for cciw.co.uk staff functions, especially camp officers")
        self.assertTextPresent("Erase columns from 1 `accounts.User` record(s)")

        self.assertTextPresent("The following columns will be erased:")
        self.assertTextPresent("password")

        self.assertTextPresent("officers.Application")
        self.assertTextPresent("Officer's application form, required to come on camp.")


class DataErasureRequestTestsWT(DataErasureRequestTestsBase, WebTestBase):
    pass
