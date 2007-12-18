from client import CciwClient
from django.test import TestCase
from cciw.cciwmain.models import Topic

class NewsPage(TestCase):    
    fixtures = ['basic.yaml', 'test_members.yaml', 'news.yaml']

    def setUp(self):
        self.client = CciwClient()


    # Short news items contain BBCode
    def test_shortews_html(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assert_("Bits &amp; Pieces" in response.content,
                     "Subject not present or not escaped properly")

        self.assert_("Summary <b>with bbcode</b>" in response.content,
                     "BBCode content not present or not escaped properly")

    def test_shortnews_atom(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(topic.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)
        
        self.assert_("Bits &amp; Pieces" in response.content,
                     "Subject not present or not escaped properly")

        self.assert_("Summary &lt;b&gt;with bbcode&lt;/b&gt;" in response.content,
                     "BBCode content not present or not escaped properly")


    # `Long' news items contain HTML
    def test_longnews_html(self):
        topic = Topic.objects.get(id=2)
        response = self.client.get(topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assert_("Fish &amp; Chips" in response.content,
                     "Subject not present or not escaped properly")

        self.assert_("<p>Full item with <i>html" in response.content,
                     "HTML content not present or not escaped properly")


    def test_longnews_atom(self):
        topic = Topic.objects.get(id=2)
        response = self.client.get(topic.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)

        self.assert_("Fish &amp; Chips" in response.content,
                     "Subject not present or not escaped properly")
        
        self.assert_("&lt;p&gt;Full item with &lt;i&gt;html" in response.content,
                     "HTML content not present or not escaped properly")
