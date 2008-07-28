# some models for use in tagging
from cciw.cciwmain.models import Member, Post, Topic
# the Tag model
from cciw.tagging.models import Tag
from cciw.tagging.utils import get_content_type_id, get_pk_as_str
from django.test import TestCase

class TestTagBase(TestCase):
    fixtures = ['basic.yaml', 'basic_topic.yaml', 'test_members.yaml']

    def tearDown(self):
        Tag.objects.all().delete()

    @staticmethod
    def _get_member():
        return Member.objects.get(user_name='test_member_1')

    @staticmethod
    def _get_member2():
        return Member.objects.get(user_name='test_poll_creator_1')

    @staticmethod
    def _get_post():
        return Post.objects.get(pk=1)

    @staticmethod
    def _get_topic():
        return Topic.objects.get(pk=1)

    @staticmethod
    def _make_tags(post=None, topic=None, member=None, member2=None):
        t1 = Tag(text='test', target=post, creator=member)
        t1.save()
        t2 = Tag(text='another', target=post, creator=member)
        t2.save()
        t3 = Tag(text='test', target=topic, creator=member)
        t3.save()
        t4 = Tag(text='test', target=post, creator=member2)
        t4.save()
        return (t1, t2, t3, t4)

    @staticmethod
    def _make_standard_tags():
        TestTagBase._make_tags(post=TestTagBase._get_post(), 
                               topic=TestTagBase._get_topic(), 
                               member=TestTagBase._get_member(),
                               member2=TestTagBase._get_member2())

class TestTag(TestTagBase):

    def test_create(self):
        """
        Test basic creation, implicitly testing GenericForeignKey
        and related utility functions.
        """
        m = self._get_member()
        p = self._get_member()
        t = Tag(text='test', target=p, creator=m)
        t.save()

        t = Tag.objects.get(text='test')
        self.assertEqual(t.target, p)
        self.assertEqual(get_pk_as_str(p), t.target_id)
        self.assertEqual(get_content_type_id(p), t.target_ct_id)

        self.assertEqual(t.creator, m)
        self.assertEqual(get_pk_as_str(m), t.creator_id)
        self.assertEqual(get_content_type_id(m), t.creator_ct_id)

    def test_delete_target(self):
        """
        Ensure that tags are deleted when their targets are
        """
        m = self._get_member()
        p = self._get_post()
        t = Tag(text='test', target=p, creator=m)
        t.save()

        p_id = get_pk_as_str(p) # p.delete will set p.id = None
        self.assertEqual(Tag.objects.filter(target_id=p_id).count(), 1)
        p.delete()
        self.assertEqual(Tag.objects.filter(target_id=p_id).count(), 0)

    def test_delete_creator(self):
        """
        Ensure that tags are deleted when their creators are
        """
        m = Member.objects.get(user_name='test_member_1')
        p = Post.objects.get(pk=1)
        t = Tag(text='test', target=p, creator=m)
        t.save()

        m_id = get_pk_as_str(m) # m.delete will set m.id = None
        self.assertEqual(Tag.objects.filter(creator_id=m_id).count(), 1)        
        m.delete()
        self.assertEqual(Tag.objects.filter(creator_id=m_id).count(), 0)

class TestGetTargets(TestTagBase):
    """
    Tests for the Tag.get_targets method.
    """
    fixtures = ['basic.yaml', 'basic_topic.yaml', 'test_members.yaml']

    def tearDown(self):
        Tag.objects.all().delete()    

    def test_get_text(self):
        """
        Tests simply asking for a 'text' value
        """
        p = self._get_post()
        tp = self._get_topic()
        self._make_standard_tags()

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test')],
                         [('test', p, 2), ('test', tp, 1)])

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('another')],
                         [('another', p, 1)])

    def test_get_text_list(self):
        """
        Tests asking for a list of 'text' values
        """
        p = self._get_post()
        m2 = self._get_member2()
        tp = self._get_topic()
        self._make_standard_tags()

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets(['test', 'another'])],
                         [('test another', p, 2)])

        # Add some more data to really test
        Tag(text='another', creator=m2, target=p).save()
        Tag(text='another', creator=m2, target=tp).save()

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets(['test', 'another'])],
                         [('test another', p, 4),
                          ('test another', tp, 1)])

    def test_get_text_for_model(self):
        p = self._get_post()
        tp = self._get_topic()
        self._make_standard_tags()

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test', target_model=Post)],
                         [('test', p, 2)])

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test', target_model=Topic)],
                         [('test', tp, 1)])

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test', target_model=Member)],
                         [])

    def test_get_text_with_limit_offset(self):
        p = self._get_post()
        tp = self._get_topic()
        self._make_standard_tags()

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test', limit=1)],
                         [('test', p, 2)])

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test', limit=10, offset=1)],
                         [('test', tp, 1)])

        self.assertEqual([(tt.text, tt.target, tt.count) for tt in Tag.objects.get_targets('test', limit=10, offset=2)],
                         [])

    def test_get_text_counts(self):
        """
        Tests get_target_count, simply asking for a 'text' value
        """
        self._make_standard_tags()

        self.assertEqual(Tag.objects.get_target_count('test'), 2)
        self.assertEqual(Tag.objects.get_target_count('another'), 1)

    def test_get_text_for_model_counts(self):
        self._make_standard_tags()

        self.assertEqual(Tag.objects.get_target_count('test', target_model=Post), 1)
        self.assertEqual(Tag.objects.get_target_count('test', target_model=Member), 0)

class TestTagSummaries(TestTagBase):
    def setUp(self):
        super(TestTagSummaries, self).setUp()
        self._make_standard_tags()

    def test_tag_summaries(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries()],
                         [('test', 3),
                          ('another', 1)])

    def test_tag_summaries_limit(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(limit=1)],
                         [('test', 3)])

    def test_tag_summaries_order_text(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(order='text')],
                         [('another', 1),
                          ('test', 3)])

    def test_tag_summaries_text(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(text='another')],
                         [('another', 1)])

    def test_tag_summaries_target_model(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(target_model=Post, order='text')],
                         [('another', 1),
                          ('test', 2)])

    def test_tag_summaries_creator(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(creator=self._get_member(), order='text')],
                         [('another', 1),
                          ('test', 2)])

    def test_tag_summaries_target(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(target=self._get_post(), order='text')],
                         [('another', 1),
                          ('test', 2)])
                   
    def test_tag_summaries_target2(self):
        self.assertEqual([(ts.text, ts.count) for ts in Tag.objects.get_tag_summaries(target=self._get_topic(), order='text')],
                         [('test', 1)])
                   
