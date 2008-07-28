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


