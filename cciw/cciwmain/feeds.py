from django.contrib.syndication import feeds
from django.http import Http404, HttpResponse
from cciw.cciwmain.models import Member, Topic, Post, NewsItem
from django.contrib.sites.models import Site
from django.utils.feedgenerator import Atom1Feed
from cciw.cciwmain.utils import get_member_href

MEMBER_FEED_MAX_ITEMS = 20
NEWS_FEED_MAX_ITEMS = 20
POST_FEED_MAX_ITEMS = 20
TOPIC_FEED_MAX_ITEMS = 20

# My extensions to django's feed:
#  - items() checks for self.query_set and uses that if available, otherwise
#    does a default query
#  - feed class stores the template name for convenience

# Part of this is borrowed from django.contrib.syndication.views
def handle_feed_request(request, feed_class, query_set=None, param=None):
    """If the request has 'format=atom' in the query string,
    create a feed and return it, otherwise return None."""
    
    if request.GET.get('format', None) != 'atom':
        return None

    template_name = feed_class.template_name
    feed_inst = feed_class(template_name, request.path + "?format=atom")
    if query_set is not None:
        # The Feed subclass may or may not use this query_set
        # If it is a CCIWFeed it will.
        feed_inst.query_set = query_set

    if not hasattr(feed_inst, 'link'):
        # Default: atom feed is at same location
        # as HTML page, but with different query parameters
        feed_inst.link = request.path

    try:
        feedgen = feed_inst.get_feed(param)
    except feeds.FeedDoesNotExist:
        raise Http404, "Invalid feed parameters: %r." % param

    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response
    
def add_domain(url):
    """Adds the domain onto the beginning of a URL"""
    return feeds.add_domain(Site.objects.get_current().domain, url)

class CCIWFeed(feeds.Feed):
    feed_type = Atom1Feed
    def items(self):
        query_set = getattr(self, 'query_set', None)
        if query_set is None:
            query_set = self.default_query()
        else:
            return self.modify_query(query_set)

class MemberFeed(CCIWFeed):
    template_name = 'members'
    title = "New CCIW Members"
    description = "New members of the Christian Camps in Wales message boards."

    def default_query(self):
        return Member.visible_members.all()
        
    def modify_query(self, query_set):
        return  query_set.order_by('-date_joined')[:MEMBER_FEED_MAX_ITEMS]

class PostFeed(CCIWFeed):
    template_name = 'posts'
    title = "CCIW message boards posts"
    
    def default_query(self):
        return Post.visible_posts.all()

    def modify_query(self, query_set):
        return query_set.order_by('-posted_at')[:POST_FEED_MAX_ITEMS]
        
    def item_author_name(self, post):
        return post.posted_by_id

    def item_author_link(self, post):
        return add_domain(get_member_href(post.posted_by_id))

    def item_pubdate(self, post):
        return post.posted_at

def member_post_feed(member):
    """Returns a Feed class suitable for the posts
    of a specific member."""
    class MemberPostFeed(PostFeed):
        title = "Posts by %s" % member.user_name
        
        def default_query(self):
            return member.posts.all()
    return MemberPostFeed

class TopicFeed(CCIWFeed):
    template_name = 'topics'
    title = 'CCIW message board topics'
    
    def default_query(self):
        return Topic.visible_topics.all()
        
    def modify_query(self, query_set):
        return query_set.order_by('-created_at')[:TOPIC_FEED_MAX_ITEMS]
        
    def item_author_name(self, topic):
        return topic.started_by_id
        
    def item_author_link(self, topic):
        return add_domain(get_member_href(topic.started_by_id))
        
    def item_pubdate(self, topic):
        return topic.created_at
