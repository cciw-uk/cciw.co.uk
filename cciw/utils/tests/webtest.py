import os
import time
import unittest
from urllib.parse import urlparse

from compressor.filters import CompilerFilter
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django_functest import FuncSeleniumMixin, FuncWebTestMixin, ShortcutLoginMixin

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


@unittest.skipIf(os.environ.get('SKIP_SELENIUM_TESTS'), "Skipping Selenium tests")
class SeleniumBase(ShortcutLoginMixin, CommonMixin, FuncSeleniumMixin, TestBaseMixin, StaticLiveServerTestCase):
    """
    Base class for Selenium tests.
    """
    driver_name = 'Firefox'
    browser_window_size = (1024, 768)
    display = TESTS_SHOW_BROWSER
    default_timeout = 20
    page_load_timeout = 40

    def assertCode(self, status_code):
        pass

    def assertHtmlPresent(self, html):
        self.assertContains(self._get_page_source(), html, html=True)

    def wait_for_ajax(self):
        time.sleep(0.1)
        self.wait_until(lambda driver: driver.execute_script('return (typeof(jQuery) == "undefined" || jQuery.active == 0)'))
