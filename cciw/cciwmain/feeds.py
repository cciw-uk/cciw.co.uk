from django.contrib.syndication import feeds
from django.http import Http404, HttpResponse
from cciw.cciwmain.models import Member
from django.utils.feedgenerator import Atom1Feed

MEMBER_FEED_MAX_ITEMS = 20

# My extensions to django's feed:
#  - items() checks for self.query_set and uses that if available, otherwise
#    does a default query
#  - feed class stores the template name for convenience

class MemberFeed(feeds.Feed):
    feed_type = Atom1Feed
    template_name = 'members'
    title = "New CCIW Members"
    link = "/members/"
    description = "New members of the Christian Camps in Wales message boards."
    
    def items(self):
        if getattr(self, 'query_set', None) is None:
            self.query_set = Member.objects.all()
        return  self.query_set.exclude(banned=True, hidden=True).order_by('-date_joined')[:MEMBER_FEED_MAX_ITEMS]

# Part of this is borrowed from django.contrib.syndication.views
def handle_feed_request(request, feed_class, query_set=None, param=None):
    """If the request has 'format=atom' in the query string,
    create a feed and return it, otherwise return None."""
    
    if request.GET.get('format', None) != 'atom':
        return None

    template_name = feed_class.template_name
    feed_inst = feed_class(template_name, request.path)
    if query_set is not None:
        # In case the Feed subclass can use query_set
        feed_inst.query_set = query_set

    try:
        feedgen = feed_inst.get_feed(param)
    except feeds.FeedDoesNotExist:
        raise Http404, "Invalid feed parameters. Slug %r is valid, but other parameters, or lack thereof, are not." % slug

    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response
