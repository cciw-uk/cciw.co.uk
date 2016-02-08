from urllib.parse import urlparse

from compressor.filters import CompilerFilter
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django_functest import FuncWebTestMixin, ShortcutLoginMixin


# We don't need less compilation when running normal tests, and it adds a lot to
# the test run.
class DummyLessCssFilter(CompilerFilter):
    def __init__(self, content, command=None, *args, **kwargs):
        pass

    def input(self, **kwargs):
        return ''


@override_settings(COMPRESS_PRECOMPILERS=[('text/less', 'cciw.utils.tests.webtest.DummyLessCssFilter')],
                   )
class WebTestBase(ShortcutLoginMixin, FuncWebTestMixin, TestCase):
    """
    Base class for integration tests that need more than Django's test Client.
    """
    def officer_login(self, creds):
        self.shortcut_login(username=creds[0],
                            password=creds[1])

    def officer_logout(self):
        self.shortcut_logout()

    def assertCode(self, status_code):
        self.assertEqual(self.last_response.status_code, status_code)

    def auto_follow(self):
        if str(self.last_response.status_code).startswith('3'):
            self.last_responses.append(self.last_response.follow())
        return self.last_response

    def assertNamedUrl(self, urlname):
        url = reverse(urlname)
        path = urlparse(self.last_response.request.url).path
        # response.url doesn't work in current version of django_webtest
        self.assertEqual(path, url)

    def assertHtmlPresent(self, html):
        self.assertContains(self.last_response, html, html=True)
