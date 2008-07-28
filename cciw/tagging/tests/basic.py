# some models for use in tagging
from cciw.cciwmain.models import Member, Post
# the Tag model
from cciw.tagging.models import Tag
from cciw.tagging.utils import get_content_type_id, get_pk_as_str
from django.test import TestCase


class TestTag(TestCase):
    fixtures = ['basic.yaml', 'basic_topic.yaml', 'test_members.yaml']

    def tearDown(self):
        Tag.objects.all().delete()

    def test_create(self):
        """
        Test basic creation, implicitly testing GenericForeignKey
        and related utility functions.
        """
        m = Member.objects.get(user_name='test_member_1')
        p = Post.objects.get(pk=1)
        t = Tag(text='test')
        t.target = p
        t.creator = m
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
        m = Member.objects.get(user_name='test_member_1')
        p = Post.objects.get(pk=1)
        t = Tag(text='test')
        t.target = p
        t.creator = m
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
        t = Tag(text='test')
        t.target = p
        t.creator = m
        t.save()

        m_id = get_pk_as_str(m) # m.delete will set m.id = None
        self.assertEqual(Tag.objects.filter(creator_id=m_id).count(), 1)        
        m.delete()
        self.assertEqual(Tag.objects.filter(creator_id=m_id).count(), 0)
