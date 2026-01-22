import pytest
from django.conf import settings

BROWSER = "Firefox"
SHOW_BROWSER = False


def pytest_addoption(parser):
    parser.addoption(
        "--browser", type=str, default="Firefox", help="Selenium driver_name to use", choices=["Firefox", "Chrome"]
    )
    parser.addoption("--show-browser", action="store_true", default=False, help="Show web browser window")


def pytest_configure(config):
    global SHOW_BROWSER, BROWSER
    BROWSER = config.option.browser
    SHOW_BROWSER = config.option.show_browser


@pytest.fixture(autouse=True)
def cciw_all():
    import cciw.cciwmain.common

    cciw.cciwmain.common._thisyear = None
    cciw.cciwmain.common._thisyear_timestamp = None

    # To get our custom email backend to be used, we have to patch settings
    # at this point, due to how Django's test runner also sets this value:
    settings.EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"
