from client import CciwClient
from django.test import TestCase

from cciw.cciwmain.models import Forum

class TopicPage(TestCase):
    fixtures = ['basic.yaml', 'test_members.yaml', 'basic_topic.yaml']

    def setUp(self):
        self.client = CciwClient()

    def test_topic_html(self):
        response = self.client.get('/camps/2001/1/forum/1/')
        print response.content
        

    def test_topic_atom(self):
        response = self.client.get('/camps/2001/1/forum/1/?format=atom')
        print response.content

    
