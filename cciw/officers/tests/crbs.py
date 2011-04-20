from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from twill.shell import TwillCommandLoop
from twill import commands as tc

from cciw.officers.tests.references import OFFICER, LEADER
from cciw.utils.tests.twillhelpers import TwillMixin, make_django_url, make_twill_url


class CRBForm(TwillMixin, TestCase):

    fixtures = ['basic.json', 'officers_users.json']

    def test_add_crb(self):
        self._twill_login(OFFICER)
        u = User.objects.get(username=OFFICER[0])
        assert len(u.crbapplication_set.all()) == 0
        tc.go(make_django_url('cciw.officers.views.add_crb'))
        tc.code(200)
        tc.formvalue('1', 'crb_number', '123456')
        tc.formvalue('1', 'completed', '2010-05-06')
        tc.submit()
        tc.url(reverse('cciw.officers.views.index'))
        self.assertEqual(len(u.crbapplication_set.all()), 1)
