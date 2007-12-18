from client import CciwClient
from django.test import TestCase
from cciw.cciwmain.models import Topic

class TopicPage(TestCase):
    fixtures = ['basic.yaml', 'test_members.yaml', 'basic_topic.yaml']

    def setUp(self):
        self.client = CciwClient()
        
    def path(self):
        return Topic.objects.get(id=1).get_absolute_url()

    def test_topic_html(self):
        response = self.client.get(self.path())
        self.failUnlessEqual(response.status_code, 200)
        self.assert_("<h2>&lt;Jill &amp; Jane&gt;</h2>" in response.content, 
                     "Subject not escaped correctly")
        self.assert_("A <b>unique message</b> with some bbcode &amp; &lt;stuff&gt; to be escaped" in response.content, 
                     "Posts not escaped correctly")
        self.assert_('<a href="/camps/">Forums and photos</a>' in response.content, 
                     "Breadcrumb not escaped properly")

    def test_topic_atom(self):
        response = self.client.get(self.path(), {'format':'atom'})
        self.failUnlessEqual(response.status_code, 200)
        self.assert_('<title>CCIW - Posts on topic "&lt;Jill &amp; Jane&gt;"</title>' in response.content,
                     "Title not escaped properly")
        self.assert_('A &lt;b&gt;unique message&lt;/b&gt; with some bbcode &amp;amp; &amp;lt;stuff&amp;gt; to be escaped' in response.content,
                     "Message posts not escaped properly")

