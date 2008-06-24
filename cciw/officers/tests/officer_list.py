import twill
from twill.shell import TwillCommandLoop
from twill import commands as tc
from cciw.cciwmain.tests.twillhelpers import TwillMixin, make_django_url
from django.test import TestCase
from django.core.urlresolvers import reverse
from cciw.officers.tests.references import LEADER, OFFICER, ReferencesPage


class OfficerListPage(TwillMixin, TestCase):
    fixtures = ['basic.yaml', 'officers_users.yaml', 'references.yaml']
    def test_page_ok(self):
        self._twill_login(LEADER)
        tc.go(make_django_url("cciw.officers.views.officer_list", year=2000, number=1))
        tc.code(200)

        # Complete list of officers
        tc.find("""<h3>List for email:</h3>
<p>
"Mr Leader" &lt;leader@somewhere.com&gt;,"Mr Officer" &lt;officer1@somewhere.com&gt;,"Mr Officer2" &lt;officer2@somewhere.com&gt;,
</p>""")

        # Officers without application forms. 
        # (This is not brilliantly robust, because both lists are on one
        #  page, but it will do.)
        tc.find("""<h3>List for email:</h3>
<p>
"Mr Leader" &lt;leader@somewhere.com&gt;,
</p>""")


