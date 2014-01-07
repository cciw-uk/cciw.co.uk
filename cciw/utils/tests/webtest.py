from django_webtest import WebTest
from django.core.urlresolvers import reverse

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

    def fill(self, form, data):
        for k,v in data.items():
            form[k] = unicode(v)
        return form

    def code(self, response, status_code):
        self.assertEqual(response.status_code, status_code)

    def get(self, urlname, *args, **kwargs):
        return self.app.get(reverse(urlname, args=args, kwargs=kwargs))
