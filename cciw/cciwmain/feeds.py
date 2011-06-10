from django.contrib.syndication import views as feed_views
from django.utils.feedgenerator import Atom1Feed

MEMBER_FEED_MAX_ITEMS = 20
NEWS_FEED_MAX_ITEMS = 20
POST_FEED_MAX_ITEMS = 20
TOPIC_FEED_MAX_ITEMS = 20
PHOTO_FEED_MAX_ITEMS = 20
TAG_FEED_MAX_ITEMS = 20

# My extensions to django's feed class:
#  - items() uses self.query_set
#  - feed class stores the template name for convenience

# Part of this is borrowed from django.contrib.syndication.views
def handle_feed_request(request, feed_class, query_set=None, param=None):
    """If the request has 'format=atom' in the query string,
    create a feed and return it, otherwise return None."""

    if request.GET.get('format', None) != u'atom':
        return None

    feed_inst = feed_class()
    # Django's class does the wrong thing, need to override
    feed_inst.feed_url = request.get_full_path()

    if query_set is not None:
        # The Feed subclass may or may not use this query_set
        # If it is a CCIWFeed it will.
        feed_inst.query_set = query_set

    if not hasattr(feed_inst, 'link'):
        # Default: atom feed is at same location
        # as HTML page, but with different query parameters
        feed_inst.link = request.path

    return feed_inst(request)

def add_domain(url):
    """Adds the domain onto the beginning of a URL"""
    return feed_views.add_domain(get_current_domain(), url, secure=True)

class CCIWFeed(feed_views.Feed):

    feed_type = Atom1Feed

    def items(self):
        return self.modify_query(self.query_set)

    @property
    def title_template(self):
        return 'feeds/%s_title.html' % self.template_name

    @property
    def description_template(self):
        return 'feeds/%s_description.html' % self.template_name

class MemberFeed(CCIWFeed):
    template_name = 'members'
    title = u"New CCIW Members"
    description = u"New members of the Christian Camps in Wales message boards."

    def modify_query(self, query_set):
        return  query_set.order_by('-date_joined')[:MEMBER_FEED_MAX_ITEMS]

class PostFeed(CCIWFeed):
    template_name = 'posts'
    title = u"CCIW message boards posts"

    def modify_query(self, query_set):
        return query_set.select_related('topic', 'photo', 'posted_by').order_by('-posted_at')[:POST_FEED_MAX_ITEMS]

    def item_author_name(self, post):
        return post.posted_by.user_name

    def item_author_link(self, post):
        return add_domain(get_member_href(post.posted_by.user_name))

    def item_pubdate(self, post):
        return post.posted_at

def member_post_feed(member):
    """Returns a Feed class suitable for the posts
    of a specific member."""
    class MemberPostFeed(PostFeed):
        title = u"CCIW - Posts by %s" % member.user_name
    return MemberPostFeed

def topic_post_feed(topic):
    """Returns a Feed class suitable for the posts
    in a specific topic."""
    class TopicPostFeed(PostFeed):
        title = u"CCIW - Posts on topic \"%s\"" % topic.subject
    return TopicPostFeed

def photo_post_feed(photo):
    """Returns a Feed classs suitable for the posts in a specific photo."""
    class PhotoPostFeed(PostFeed):
        title = u"CCIW - Posts on photo %s" % unicode(photo)
    return PhotoPostFeed

class TopicFeed(CCIWFeed):
    template_name = 'topics'
    title = u"CCIW - message board topics"

    def modify_query(self, query_set):
        return query_set.order_by('-created_at')[:TOPIC_FEED_MAX_ITEMS]

    def item_author_name(self, topic):
        return topic.started_by.user_name

    def item_author_link(self, topic):
        return add_domain(get_member_href(topic.started_by.user_name))

    def item_pubdate(self, topic):
        return topic.created_at

def forum_topic_feed(forum):
    """Returns a Feed class suitable for topics of a specific forum."""
    class ForumTopicFeed(TopicFeed):
        title = u"CCIW - new topics in %s" % forum.nice_name()
    return ForumTopicFeed

class PhotoFeed(CCIWFeed):
    template_name = 'photos'
    title = u'CCIW photos'

    def modify_query(self, query_set):
        return query_set.order_by('-created_at')[:PHOTO_FEED_MAX_ITEMS]

    def item_pubdate(self, photo):
        return photo.created_at

def gallery_photo_feed(gallery_name):
    class GalleryPhotoFeed(PhotoFeed):
        title = gallery_name
    return GalleryPhotoFeed


from cciw.cciwmain.common import get_member_href, get_current_domain
