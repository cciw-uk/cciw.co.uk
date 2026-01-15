import os
import time
from urllib.parse import urlparse

import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django_functest import FuncSeleniumMixin, FuncWebTestMixin, MultiThreadedLiveServerMixin, ShortcutLoginMixin
from pyquery import PyQuery

import conftest
from cciw.accounts.models import User
from cciw.cciwmain.models import Person
from cciw.utils.tests.base import TestBase, TestBaseMixin


class CommonMixin:
    def officer_login(self, user_or_creds: User | Person | tuple[str, str] | None = None):
        """
        Log in an officer, using the given User, Person, or (username, password) combo,
        or None for any officer.
        """
        if user_or_creds is None:
            from cciw.officers.tests import factories as officers_factories

            user_or_creds = officers_factories.get_any_officer()
        if isinstance(user_or_creds, User):
            self.shortcut_login(user_or_creds)
            return user_or_creds
        elif isinstance(user_or_creds, Person):
            users = user_or_creds.users.all()
            if not users:
                raise AssertionError(f"Can't login for Person {user_or_creds}, no user associated")
            elif len(users) > 1:
                raise AssertionError(f"More than one user associated with Person {user_or_creds}, can't log in")
            else:
                return self.officer_login(users[0])
        elif isinstance(user_or_creds, tuple):
            username, password = user_or_creds
            self.shortcut_login(username=username, password=password)
            return User.objects.get(username=username)
        else:
            raise AssertionError(f"Don't know what to do with {type(user_or_creds)}")

    def officer_logout(self):
        self.shortcut_logout()

    def assertNamedUrl(self, urlname):
        url = reverse(urlname)
        path = urlparse(self.current_url).path
        assert path == url

    def assertElementText(self, css_selector, text):
        assert self.get_element_inner_text(css_selector) == text

    def submit_expecting_html5_validation_errors(self, submit_css_selector=None):
        """
        Submit a form, checking for and clearing HTML5 validation
        errors
        """
        # Requires `self.submit_css_selector` to be set, or
        # `submit_css_selector` to be passed as argument.
        if self.is_full_browser_test:
            # HTML5 validation to deal with
            if submit_css_selector is None:
                submit_css_selector = self.submit_css_selector
            self.click(self.submit_css_selector)
            assert self.is_element_present("form:invalid")
            self.execute_script(
                "document.querySelectorAll('[required]').forEach((elem) => elem.removeAttribute('required'))"
            )
            # Now we can go ahead and submit normally
        if submit_css_selector is None:
            # This can work if subclass has overridden `submit` to provide
            # the right css_selector by default
            self.submit()
        else:
            self.submit(submit_css_selector)


@pytest.mark.webtest
class WebTestBase(ShortcutLoginMixin, CommonMixin, FuncWebTestMixin, TestBase):
    """
    Base class for integration tests that need more than Django's test Client.
    """

    # disable django-webtest's monkey business which doesn't work with our auth
    # backend:
    setup_auth = False

    def assertCode(self, status_code):
        assert self.last_response.status_code == status_code, (
            f"Expected {status_code}, got {self.last_response.status_code}"
        )

    def auto_follow(self):
        if str(self.last_response.status_code).startswith("3"):
            self.last_responses.append(self.last_response.follow())
        return self.last_response

    def assertHtmlPresent(self, html):
        self.assertContains(self.last_response, html, html=True)

    def add_admin_inline_form_to_page(self, inline_name, count=1):
        """
        For Django admin pages that have a hidden form template for an inline,
        converts it to a real form that can be used.  Needed for WebTest
        tests as an equivalent to clicking "add new [thing]".
        """
        pq = PyQuery(self.last_response.body)
        parent = pq.find(f"#{inline_name}-group")
        total_forms_elem = pq.find(f"#id_{inline_name}-TOTAL_FORMS")
        form_count = int(total_forms_elem.val())
        template = pq.find(f"#{inline_name}-empty")
        for i in range(0, count):
            new_form_number = form_count + i
            new_form = template.html().replace("__prefix__", str(new_form_number))
            parent.append(new_form)
        total_forms_elem.val(str(form_count + count))
        self.last_response.body = pq.html().encode("utf-8")


@pytest.mark.selenium
class SeleniumBase(
    ShortcutLoginMixin,
    CommonMixin,
    FuncSeleniumMixin,
    TestBaseMixin,
    MultiThreadedLiveServerMixin,
    StaticLiveServerTestCase,
):
    """
    Base class for Selenium tests.
    """

    driver_name = conftest.BROWSER
    browser_window_size = (1600, 900)
    display = conftest.SHOW_BROWSER
    default_timeout = 20
    page_load_timeout = 40

    @classmethod
    def get_webdriver_options(cls):
        kwargs = {}
        if cls.driver_name == "Firefox":
            firefox_binary = os.environ.get("TEST_SELENIUM_FIREFOX_BINARY", None)
            if firefox_binary is not None:
                from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

                kwargs["firefox_binary"] = FirefoxBinary(firefox_path=firefox_binary)
        return kwargs

    def assertCode(self, status_code):
        pass

    def assertHtmlPresent(self, html):
        self.assertContains(self._get_page_source(), html, html=True)

    def wait_for_ajax(self):
        time.sleep(0.1)
        self.wait_until(
            lambda driver: driver.execute_script('return (typeof(jQuery) == "undefined" || jQuery.active == 0)')
        )
        self.wait_until(
            lambda _: not self.is_element_present(".htmx-request")
            and not self.is_element_present(".htmx-swapping")
            and not self.is_element_present(".htmx-settling")
        )
