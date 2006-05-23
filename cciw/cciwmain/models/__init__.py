from members import Permission, Member, Award, PersonalAward, Message
from camps import Site, Person, Camp
from forums import Forum, NewsItem, Topic, Gallery, Photo, Post
from polls import Poll, PollOption, VoteInfo
from sitecontent import MenuLink, HtmlChunk

# TODO - work out where to put this:
from cciw.tagging.fields import add_tagging_fields
from cciw.tagging.utils import register_mappers, register_renderer
import cciw.cciwmain.utils
from django.template.defaultfilters import escape

register_mappers(Post, str, int)
register_mappers(Topic, str, int)
register_mappers(Photo, str, int)
register_mappers(Member, str, str)
add_tagging_fields(creator_model=Member, creator_attrname='all_tags')
add_tagging_fields(creator_model=Member, creator_attrname='post_tags', target_model=Post, target_attrname='tags')
add_tagging_fields(creator_model=Member, creator_attrname='topic_tags', target_model=Topic, target_attrname='tags')
add_tagging_fields(creator_model=Member, creator_attrname='photo_tags', target_model=Photo, target_attrname='tags')
add_tagging_fields(creator_model=Member, creator_attrname='member_tags', target_model=Post, target_attrname='tags')

def render_post(post):
    return '<a href="%s">Post by %s: %s...</a>' % \
        (post.get_absolute_url(), post.posted_by_id, escape(cciw.cciwmain.utils.get_extract(post.message, 30)))
    
register_renderer(Member, Member.get_link)
register_renderer(Post, render_post)
