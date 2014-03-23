from __future__ import with_statement
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from cciw.forums.models import Topic, Member, NewsItem, Post, Forum
from cciw.cciwmain.tests.members import TEST_MEMBER_USERNAME
from cciw.cciwmain.tests.client import CciwClient, RequestFactory
from cciw.cciwmain.tests.utils import init_query_caches, FuzzyInt
from cciw.forums.views import forums as forums_views


class NewsPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'news.json']

    def setUp(self):
        self.client = CciwClient()


    # Short news items contain BBCode
    def test_shortews_html(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Bits &amp; Pieces")

        self.assertContains(response, "Summary <b>with bbcode</b>")

    def test_shortnews_atom(self):
        topic = Topic.objects.get(id=1)
        response = self.client.get(topic.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Bits &amp; Pieces")
        self.assertContains(response, "Summary &lt;b&gt;with bbcode&lt;/b&gt;")

    # `Long' news items contain HTML
    def test_longnews_html(self):
        topic = Topic.objects.get(id=2)
        response = self.client.get(topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Fish &amp; Chips")
        self.assertContains(response, "<p>Full item with <i>html")

    def test_longnews_atom(self):
        topic = Topic.objects.get(id=2)
        response = self.client.get(topic.forum.get_absolute_url(), {'format':'atom'})
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Fish &amp; Chips")
        self.assertContains(response, "&lt;p&gt;Full item with &lt;i&gt;html")

class AllNewsPage(TestCase):

    fixtures = ['basic.json', 'test_members.json', 'news.json']

    def test_query_count(self):
        """
        Test the number of queries (HTML and Atom)
        """
        path = reverse('cciwmain.site-news-index')
        member = Member.objects.get(user_name=TEST_MEMBER_USERNAME)
        forum = Forum.objects.get(location='news/')
        factory = RequestFactory()
        init_query_caches()

        # Make sure we have lots of news items
        num = 100
        assert num > settings.FORUM_PAGINATE_TOPICS_BY
        for i in range(num):
            news_item = NewsItem.create_item(member, "Subject %s" % i,
                                             "Short item %s" % i)
            topic = Topic.create_topic(member, "Topic %s" % i, forum)
            topic.news_item = news_item
            topic.save()
            Post.create_post(member, "Message %s" % i, topic, None)

        request = factory.get(path)
        with self.assertNumQueries(FuzzyInt(1, 5)):
            resp = forums_views.news(request)
            resp.render()
            expected_count = settings.FORUM_PAGINATE_NEWS_BY
            self.assertContains(resp, "<a title=\"Information about",
                                count=FuzzyInt(expected_count, expected_count + 2))

        request = factory.get(path, {'format':'atom'})
        with self.assertNumQueries(2):
            response = forums_views.news(request)
            resp.render()
            self.assertTrue(response['Content-Type'].startswith('application/atom+xml'))
