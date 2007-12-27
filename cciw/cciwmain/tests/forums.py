from client import CciwClient
from members import TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD, TEST_POLL_CREATOR_USERNAME, TEST_POLL_CREATOR_PASSWORD 
from django.test import TestCase
from cciw.cciwmain.models import Topic, Member, Poll
from django.core.urlresolvers import reverse
from datetime import datetime

FORUM_1_YEAR = 2000
FORUM_1_CAMP_NUMBER = 1
ADD_POLL_URL =  reverse("cciwmain.camps.add_poll", 
                        kwargs=dict(year=FORUM_1_YEAR, number=FORUM_1_CAMP_NUMBER))

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

class CreatePollPage(TestCase):
    fixtures = ['basic.yaml', 'test_members.yaml', 'basic_topic.yaml']

    def setUp(self):
        self.client = CciwClient()

    def _poll_data_1(self):
        return dict(
            title="Poll title",
            intro_text="This is a poll",
            polloptions="Option 1\nOption 2\nOption 3\n\nOption 4",
            outro_text="Outro text",
            voting_starts_0="2007-12-26",
            voting_starts_1="00:00",
            voting_ends_0="2007-12-29",
            voting_ends_1="00:00",
            rules="0",
            rule_parameter="1",
            )
    def test_cant_create_poll_if_anonymous(self):        
        response = self.client.get(ADD_POLL_URL)
        # we should get a redirect to login page
        self.assertEqual(response.status_code, 302)

    def test_cant_create_poll_if_not_poll_creator(self):
        self.client.member_login(TEST_MEMBER_USERNAME, TEST_MEMBER_PASSWORD)
        response = self.client.get(ADD_POLL_URL)
        # we should a permission denied
        self.assertEqual(response.status_code, 403, "Should get permission denied if trying to create a poll w/o enough permissions")

    def test_create_poll(self):
        poll_data = self._poll_data_1()
        # Precondition:
        self.assertEqual(Poll.objects.filter(title=poll_data['title']).count(), 0, "Precondition for test not satisfied")

        self.client.member_login(TEST_POLL_CREATOR_USERNAME, TEST_POLL_CREATOR_PASSWORD)
        response = self.client.get(ADD_POLL_URL)
        # we should be OK
        self.failUnlessEqual(response.status_code, 200)

        # Now do a post to the same URL
        response2 = self.client.post(ADD_POLL_URL, data=self._poll_data_1())

        # We get a redirection to the new page:
        self.assertEqual(response2.status_code, 302, "Should be redirected upon successful creation of poll")

        # Ensure the poll got created
        try:
            p = Poll.objects.get(title=poll_data['title'])
        except Poll.ObjectDoesNotExist:
            self.fail("Poll not created.")
        
        self.assertEqual(p.intro_text, poll_data['intro_text'])
        self.assertEqual(p.poll_options.count(), 4, "Poll does not have right number of options created")

    def test_cant_edit_someone_elses_poll(self):
        p = Poll(title="test", 
                 voting_starts=datetime.now(), 
                 voting_ends=datetime.now(),
                 rules = 0,
                 rule_parameter=1,
                 have_vote_info=True,
                 created_by_id=TEST_MEMBER_USERNAME)
        p.save()

        self.client.member_login(TEST_POLL_CREATOR_USERNAME, TEST_POLL_CREATOR_PASSWORD)
        url = reverse("cciwmain.camps.edit_poll", 
                      kwargs=dict(year=FORUM_1_YEAR, 
                                  number=FORUM_1_CAMP_NUMBER,
                                  poll_id=p.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

