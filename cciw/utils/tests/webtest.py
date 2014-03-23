from six.moves.urllib_parse import urlparse

from django_webtest import WebTest
from django.core.urlresolvers import reverse

from six import text_type

class WebTestBase(WebTest):
    """
    Base class for integration tests that need more than Django's test Client.
    """
    # This uses django_webtest, with convenience wrappers.
    def webtest_officer_login(self, creds):
        form = self.get("cciw.officers.views.index").form
        self.fill(form,
                  {'username': creds[0],
                   'password': creds[1],
                   })
        response = form.submit().follow()
        self.assertEqual(response.status_code, 200)

    def webtest_officer_logout(self):
        self.app.cookiejar.clear()

    def fill(self, form, data):
        for k,v in data.items():
            form[k] = text_type(v)
        return form

    def code(self, response, status_code):
        self.assertEqual(response.status_code, status_code)

    def get(self, urlname, *args, **kwargs):
        if '/' not in urlname:
            url = reverse(urlname, args=args, kwargs=kwargs)
        else:
            url = urlname
        return self.app.get(url)

    def assertUrl(self, response, urlname):
        url = reverse(urlname)
        path = urlparse(response.request.url).path
        # response.url doesn't work in current version of django_webtest
        self.assertEqual(path, url)
