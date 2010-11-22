from cciw.cciwmain import feeds
from cciw.cciwmain.templatetags import view_extras
from cciw.cciwmain.utils import python_to_json
from django.conf import settings
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
import cciw.middleware.threadlocals as threadlocals
import datetime
import urllib

def standard_extra_context(title=None, description=None, keywords=None):
    """
    Gets the 'extra_dict' dictionary used for all pages
    """
    from cciw.cciwmain.models import Member

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


# Class based version
class DefaultMetaData(object):
    """
    Mixin that provides some default metadata and other standard variables to the
    page context. Assumes the use of TemplateView.
    """
    metadata_title=u"Christian Camps in Wales"
    metadata_description= u"Details of camps, message boards and photos for the UK charity Christian Camps in Wales"
    metadata_keywords = u"camp, camps, summer camp, Christian, Christian camp, charity"

    def __init__(self, **kwargs):
        # Provide place for arbitrary context to get stored.
        self.context = {}
        return super(DefaultMetaData, self).__init__(**kwargs)

    def get_context_data(self, **kwargs):
        from cciw.cciwmain.models import Member
        d = standard_extra_context(title=self.metadata_title,
                                   description=self.metadata_description,
                                   keywords=self.metadata_keywords)
        # Allow context to overwrite standard_extra_context
        d.update(self.context)
        c = super(DefaultMetaData, self).get_context_data(**kwargs)
        c.update(d)
        return c


class AjaxyFormView(FormView):
    """
    A FormView subclass that enables the returning of validation results by JSON
    if accessed with ?format=json.
    """
    def post(self, request, *args, **kwargs):
        if request.GET.get('format', None) == 'json':
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            return HttpResponse(python_to_json(form.errors),
                                mimetype='text/javascript')
        else:
            return super(AjaxyFormView, self).post(request, *args, **kwargs)


class FeedHandler(object):
    """
    Mixin that handles requests for a feed rather than HTML
    """
    feed_class = None

    def get_feed_class(self):
        if self.feed_class is None:
            raise NotImplementedError("Attribute feed_class not defined.")
        else:
            return self.feed_class

    def is_feed_request(self):
        return self.request.GET.get('format', None) == 'atom'

    def get(self, request, *args, **kwargs):
        if self.is_feed_request():
            feed_class = self.get_feed_class()
            return feeds.handle_feed_request(self.request, feed_class, self.get_queryset())
        else:
            return super(FeedHandler, self).get(request, *args, **kwargs)


def object_list(request, queryset, extra_context=None,
                template_name='', paginate_by=None):
    # list_detail.object_list replacement with all the things we need
    class ObjectList(ListView):
        def get_context_data(self, **kwargs):
            c = super(ObjectList, self).get_context_data(**kwargs)
            c.update(extra_context)
            return c

    return ObjectList.as_view(template_name=template_name,
                              paginate_by=paginate_by,
                              queryset=queryset)(request)


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
                .replace('{{media}}', settings.MEDIA_URL)\
                .replace('{{static}}', settings.STATIC_URL)
standard_subs.is_safe = True # provided our substitutions don't introduce anything that must be escaped

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
    return mark_safe(u" :: ".join(links))

def standard_processor(request):
    """Processor that does standard processing of request
    that we need for all pages."""
    from cciw.cciwmain.models import MenuLink
    context = {}
    assert type(request.path) is unicode
    context['homepage'] = (request.path == u"/")
    links = MenuLink.objects.filter(parent_item__isnull=True, visible=True)
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

    context.update(view_extras.get_view_extras_context(request))

    return context
