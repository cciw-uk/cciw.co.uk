from cciw.apps.cciw.settings import *
from django.models.members import members
from django.models.sitecontent import menulinks
from django.core.extensions import DjangoContext
from cciw.apps.cciw.templatetags import view_extras
import datetime
    
class StandardContext(DjangoContext):
    """
    Provides simple construction of context needed for the 'standard.html' template and
    templates that inherit from it
    """
    def __init__(self, request, extra_dict=None, title=None, processors=None):
        if extra_dict is None: extra_dict = {}
        # modify the context dictionary, then construct the base class
        extra_dict = standard_extra_context(extra_dict, title)
        DjangoContext.__init__(self, request, extra_dict, processors=processors)
        
def standard_extra_context(extra_dict=None, title=None):
    """
    Can be used directly to get an extra context dictionary e.g. for generic views.
    Normally use via StandardContext
    """
    if extra_dict is None: 
        extra_dict = {}
        
    if title is None:
        title = "Christian Camps in Wales"
    
    extra_dict['title'] = title
    extra_dict['thisyear'] = THISYEAR
    extra_dict['pagevars'] = {
        'media_root_url': CCIW_MEDIA_ROOT,
        'style_sheet_url': CCIW_MEDIA_ROOT + 'style.css',
        'style_sheet2_url': CCIW_MEDIA_ROOT + 'style2.css',
        'html_chunks': [],
        'logged_in_members': 
            members.get_count(last_seen__gte=datetime.datetime.now() \
                                           - datetime.timedelta(minutes=3)),
    }
    
    return extra_dict

def standard_subs(value):
    """Standard substitutions made on HTML content"""
    return value.replace('{{thisyear}}', str(THISYEAR))
    #return value.replace('{{thisyear}}', str(THISYEAR)).replace('{{media}}', CCIW_MEDIA_ROOT)


def order_option_to_lookup_arg(order_options, lookup_args_dict, 
                                request, default_order_by):
    """Add a lookup argument if the request contains any of the specified ordering
    parameters in the query string.  
    
    order_options is a dict of query string params and the corresponding lookup argument.  
    
    default_order_by is value to use for if there is no matching
    order query string.
    
    lookup_args_dict is a dict of Django lookup arguments to modify inplace 
    """

    order_request = request.GET.get('order', None)
    try:
        order_by = order_options[order_request]
    except:
        order_by = default_order_by
    lookup_args_dict['order_by'] = order_by

def create_breadcrumb(links):
    return " :: ".join(links)

def standard_processor(request):
    """Processor that does standard processing of request
    that we need for all pages."""
    context = {}
    context['homepage'] = (request.path == "/")
    # TODO - filter on 'visible' attribute
    links = menulinks.get_list(where = ['parent_item_id IS NULL'])
    for l in links:
        l.title = standard_subs(l.title)
        l.isCurrentPage = False
        l.isCurrentSection = False
        if l.url == request.path:
            l.isCurrentPage = True
        elif request.path.startswith(l.url) and l.url != '/':
            l.isCurrentSection = True
    context['menulinks'] = links
    context['current_member'] = get_current_member(request)

    context.update(view_extras.get_view_extras_context(request))
    
    return context

def get_current_member(request):
    try:
        member = members.get_object(user_name__exact = request.session['member_id'])
        # use opportunity to update last_seen data
        if (datetime.datetime.now() - member.last_seen).seconds > 60:
            member.last_seen = datetime.datetime.now()
            member.save()
        return member
    except (KeyError, members.MemberDoesNotExist):
        return None
 
