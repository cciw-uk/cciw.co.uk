from django.conf import settings
import cciw.cciwmain.models
from cciw.cciwmain.templatetags import view_extras
from django.http import HttpResponseRedirect
import cciw.middleware.threadlocals as threadlocals
import datetime
import urllib
       
def standard_extra_context(title=None, description=None, keywords=None):
    """
    Gets the 'extra_dict' dictionary used for all pages
    """
    Member = cciw.cciwmain.models.Member
        
    if title is None:
        title = u"Christian Camps in Wales"
    if description is None:
        description = u"Details of camps, message boards and photos for the UK charity Christian Camps in Wales"
    if keywords is None:
        keywords = u"camp, camps, summer camp, Christian, Christian camp, charity"
    
    extra_dict = {}
    extra_dict['title'] = title
    extra_dict['meta_description'] = description 
    extra_dict['meta_keywords'] = keywords
    extra_dict['thisyear'] = get_thisyear()
    extra_dict['misc'] = {
        'logged_in_members': 
            Member.objects.filter(last_seen__gte=datetime.datetime.now() \
                                           - datetime.timedelta(minutes=3)).count(),
    }
    
    return extra_dict

_thisyear = None
_thisyear_timestamp = None

def get_thisyear():
    """
    Get the year the website is currently on.  The website year is
    equal to the year of the last camp in the database, or the year 
    afterwards if that camp is in the past.
    """
    global _thisyear, _thisyear_timestamp
    if _thisyear is None or _thisyear_timestamp is None \
        or (datetime.datetime.now() - _thisyear_timestamp).seconds > 3600:
        from cciw.cciwmain.models import Camp
        lastcamp = Camp.objects.order_by('-end_date')[0]
        if lastcamp.is_past():
            _thisyear = lastcamp.year + 1
        else:
            _thisyear = lastcamp.year
        _thisyear_timestamp = datetime.datetime.now()
    return _thisyear

def standard_subs(value):
    """Standard substitutions made on HTML content"""
    return value.replace('{{thisyear}}', str(get_thisyear()))\
                .replace('{{media}}', settings.CCIW_MEDIA_URL)

def get_order_option(order_options, request, default_order_by):
    """Get the order_by parameter from the request, if the request 
    contains any of the specified ordering parameters in the query string.
    
    order_options is a dict of query string params and the corresponding lookup argument.  
    
    default_order_by is value to use for if there is no matching
    order query string.
    """

    order_request = request.GET.get('order', None)
    try:
        order_by = order_options[order_request]
    except:
        order_by = default_order_by
    return order_by

def create_breadcrumb(links):
    return u" :: ".join(links)

def standard_processor(request):
    """Processor that does standard processing of request
    that we need for all pages."""
    MenuLink = cciw.cciwmain.models.MenuLink
    context = {}
    assert type(request.path) is unicode
    context['homepage'] = (request.path == u"/")
    # TODO - filter on 'visible' attribute
    links = MenuLink.objects.filter(parent_item__isnull=True)
    for l in links:
        l.title = standard_subs(l.title)
        l.isCurrentPage = False
        l.isCurrentSection = False
        if l.url == request.path:
            l.isCurrentPage = True
        elif request.path.startswith(l.url) and l.url != u'/':
            l.isCurrentSection = True
    
    context['menulinks'] = links
    context['current_member'] = threadlocals.get_current_member()
    context['pagevars'] = {
        'media_root_url': settings.CCIW_MEDIA_URL,
        'style_sheet_url': settings.CCIW_MEDIA_URL + 'style.css',
    }

    context.update(view_extras.get_view_extras_context(request))
    
    return context




