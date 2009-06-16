from cciw.cciwmain.models.members import Permission, Member, Award, PersonalAward, Message
from cciw.cciwmain.models.camps import Site, Person, Camp
from cciw.cciwmain.models.forums import Forum, NewsItem, Topic, Gallery, Photo, Post
from cciw.cciwmain.models.polls import Poll, PollOption, VoteInfo
from cciw.cciwmain.models.sitecontent import MenuLink, HtmlChunk
from django.conf import settings
from django.utils.safestring import mark_safe


# TODO - work out where to put this:
from cciw.tagging.fields import add_tagging_fields
from cciw.tagging.utils import register_mappers, register_renderer
from django.utils.html import escape

register_mappers(Post, str, int)
register_mappers(Topic, str, int)
register_mappers(Photo, str, int)
register_mappers(Member, str, str)
add_tagging_fields(creator_model=Member, creator_attrname='all_tags')
add_tagging_fields(creator_model=Member, creator_attrname='post_tags', target_model=Post, target_attrname='tags')
add_tagging_fields(creator_model=Member, creator_attrname='topic_tags', target_model=Topic, target_attrname='tags')
add_tagging_fields(creator_model=Member, creator_attrname='photo_tags', target_model=Photo, target_attrname='tags')
add_tagging_fields(creator_model=Member, creator_attrname='member_tags', target_model=Member, target_attrname='tags')

def render_post(post):
    return mark_safe(u'<a href="%s">Post by %s: %s...</a>' % \
        (post.get_absolute_url(), post.posted_by_id, escape(post.message[0:30])))

def render_topic(topic):
    return mark_safe(u'<a href="%s">Topic: %s...</a>' % \
        (topic.get_absolute_url(), escape(topic.subject[0:30])))

def render_photo(photo):
     return mark_safe(u'<a href="%s"><img src="%s/photos/thumbnails/%s" alt="Photo %s" /></a>' % \
         (photo.get_absolute_url(), settings.CCIW_MEDIA_URL, photo.filename, photo.id))


register_renderer(Member, Member.get_link)
register_renderer(Post, render_post)
register_renderer(Topic, render_topic)
register_renderer(Photo, render_photo)

import cciw.cciwmain.hooks
