import os
import time
import unittest
from urllib.parse import urlparse

from compressor.filters import CompilerFilter
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django_functest import FuncSeleniumMixin, FuncWebTestMixin, ShortcutLoginMixin
from pyquery import PyQuery

from cciw.utils.tests.base import TestBase, TestBaseMixin

TESTS_SHOW_BROWSER = os.environ.get('TESTS_SHOW_BROWSER', '')


# We don't need less compilation when running normal tests, and it adds a lot to
# the test run.
class DummyLessCssFilter(CompilerFilter):
    def __init__(self, content, command=None, *args, **kwargs):
        pass

    def input(self, **kwargs):
        return ''


class CommonMixin(object):
    def officer_login(self, creds):
        self.shortcut_login(username=creds[0],
                            password=creds[1])

    def officer_logout(self):
        self.shortcut_logout()

    def assertNamedUrl(self, urlname):
        url = reverse(urlname)
        path = urlparse(self.current_url).path
        self.assertEqual(path, url)

    def assertElementText(self, css_selector, text):
        self.assertEqual(self.get_element_text(css_selector), text)

    def assert_html5_form_invalid(self):
        self.assertTrue(len(self._driver.find_elements_by_css_selector('form:invalid')),
                        1)

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
            self.assert_html5_form_invalid()
            self.execute_script('$("[required]").removeAttr("required");')
            # Now we can go ahead and submit normally
        if submit_css_selector is None:
            # This can work if subclass has overridden `submit` to provide
            # the right css_selector by default
            self.submit()
        else:
            self.submit(submit_css_selector)


@override_settings(COMPRESS_PRECOMPILERS=[('text/less', 'cciw.utils.tests.webtest.DummyLessCssFilter')],
                   )
class WebTestBase(ShortcutLoginMixin, CommonMixin, FuncWebTestMixin, TestBase):
    """
    Base class for integration tests that need more than Django's test Client.
    """
    def assertCode(self, status_code):
        self.assertEqual(self.last_response.status_code, status_code)

    def auto_follow(self):
        if str(self.last_response.status_code).startswith('3'):
            self.last_responses.append(self.last_response.follow())
        return self.last_response

    def assertHtmlPresent(self, html):
        self.assertContains(self.last_response, html, html=True)

    def get_element_text(self, css_selector):
        pq = PyQuery(self.last_response.content.decode('utf-8'))
        return pq.find(css_selector)[0].text_content()


@unittest.skipIf(os.environ.get('SKIP_SELENIUM_TESTS'), "Skipping Selenium tests")
class SeleniumBase(ShortcutLoginMixin, CommonMixin, FuncSeleniumMixin, TestBaseMixin, StaticLiveServerTestCase):
    """
    Base class for Selenium tests.
    """
    driver_name = os.environ.get('TEST_SELENIUM_DRIVER', 'Firefox')
    browser_window_size = (1024, 768)
    display = TESTS_SHOW_BROWSER
    default_timeout = 20
    page_load_timeout = 40

    @classmethod
    def get_webdriver_options(cls):
        kwargs = {}
        if cls.driver_name == 'Firefox':
            firefox_binary = os.environ.get('TEST_SELENIUM_FIREFOX_BINARY', None)
            if firefox_binary is not None:
                from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
                kwargs['firefox_binary'] = FirefoxBinary(firefox_path=firefox_binary)
        return kwargs

    def assertCode(self, status_code):
        pass

    def assertHtmlPresent(self, html):
        self.assertContains(self._get_page_source(), html, html=True)

    def get_element_text(self, css_selector):
        return self._driver.find_element_by_css_selector(css_selector).text

    def wait_for_ajax(self):
        time.sleep(0.1)
        self.wait_until(lambda driver: driver.execute_script('return (typeof(jQuery) == "undefined" || jQuery.active == 0)'))

    def accept_alert(self):
        self._driver.switch_to.alert.accept()
        time.sleep(0.2)

    def click_expecting_alert(self, css_selector):
        # TODO - fix django-functest so this isn't needed

        # Don't do wait_until_finished
        self._find(css_selector).click()
