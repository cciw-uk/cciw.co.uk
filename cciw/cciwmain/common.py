from cciw.cciwmain.settings import CCIW_MEDIA_ROOT, THISYEAR
import cciw.cciwmain.models
from cciw.cciwmain.templatetags import view_extras
from django.http import HttpResponseRedirect
import datetime
import urllib
       
def standard_extra_context(extra_dict=None, title=None):
    """
    Gets the 'extra_dict' dictionary used for all pages
    """
    Member = cciw.cciwmain.models.Member
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
        'logged_in_members': 
            Member.objects.filter(last_seen__gte=datetime.datetime.now() \
                                           - datetime.timedelta(minutes=3)).count(),
    }
    
    return extra_dict

def standard_subs(value):
    """Standard substitutions made on HTML content"""
    return value.replace('{{thisyear}}', str(THISYEAR))\
                .replace('{{media}}', CCIW_MEDIA_ROOT)


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
    return " :: ".join(links)

def standard_processor(request):
    """Processor that does standard processing of request
    that we need for all pages."""
    MenuLink = cciw.cciwmain.models.MenuLink
    context = {}
    context['homepage'] = (request.path == "/")
    # TODO - filter on 'visible' attribute
    links = MenuLink.objects.filter(parent_item__isnull=True)
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
    """Returns the currently logged in member, or None"""
    try:
        # return the val we already calculated
        return request._member
    except AttributeError:
        try:
            Member = cciw.cciwmain.models.Member
            member = Member.objects.get(user_name=request.session['member_id'])
            # use opportunity to update last_seen data
            if (datetime.datetime.now() - member.last_seen).seconds > 60:
                member.last_seen = datetime.datetime.now()
                member.save()
        except (KeyError, Member.DoesNotExist):
            member = None
        request._member = member
        return member


