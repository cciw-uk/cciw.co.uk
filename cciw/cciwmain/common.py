"""
Utility functions and base classes that are common to all views etc.
"""
import datetime
import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from cciw.cciwmain.utils import python_to_json
import cciw.middleware.threadlocals as threadlocals


# CBV baseclass functionality
class DefaultMetaData(object):
    """
    Mixin that provides some default metadata and other standard variables to the
    page context. Assumes the use of TemplateView.

    Also provides a mechanism for other context data:

     * 'extra_context' attribute can be stored on the class
       and will be used as a starting point for context data

     * After the instance has been initialised, 'context'
       will be available on the instance as a place to store context data.
    """
    metadata_title = None
    metadata_description = None
    metadata_keywords = None
    extra_context = None

    def __init__(self, **kwargs):
        # Provide place for arbitrary context to get stored.
        self.context = {}
        # Merge in statically defined context on the class, in a way that won't
        # mean that the class atttribute will be mutated.
        extra_context = self.extra_context
        if extra_context is not None:
            self.context.update(extra_context)

        return super(DefaultMetaData, self).__init__(**kwargs)

    def get_context_data(self, **kwargs):
        d = dict(title=self.metadata_title,
                 description=self.metadata_description,
                 keywords=self.metadata_keywords)
        # Allow context to overwrite
        d.update(self.context)
        c = super(DefaultMetaData, self).get_context_data(**kwargs)
        c.update(d)
        return c


def json_validation_request(request, form):
    """
    Returns a JSON validation response for a form, if the request is for JSON
    validation.
    """

    if request.GET.get('format') == 'json':
        return HttpResponse(python_to_json(form.errors),
                            mimetype='text/javascript')
    else:
        return None


# CBV equivalent to json_validation_request
class AjaxyFormMixin(object):
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
            return super(AjaxyFormMixin, self).post(request, *args, **kwargs)


class AjaxyFormView(AjaxyFormMixin, FormView):
    pass


# CBV wrapper for feeds.handle_feed_request
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
        def post(self, request, *args, **kwargs):
            return self.get(request, *args, **kwargs)

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
    """
    Processor that does standard processing of request that we need for all
    pages.
    """
    context = {}
    context['current_member'] = threadlocals.get_current_member()
    format = request.GET.get('format')
    if format is not None:
        # json or atom - we are not rendering typical pages, and don't want the
        # overhead of additional queries. This is especially important for Atom,
        # which can render many templates with separate RequestContext
        # instances.
        return context

    from cciw.sitecontent.models import MenuLink
    thisyear = get_thisyear()
    context['thisyear'] = thisyear
    assert type(request.path) is unicode
    context['homepage'] = (request.path == u"/")
    links = MenuLink.objects.filter(parent_item__isnull=True, visible=True)

    # Ugly special casing for 'thisyear' camps
    m = re.match(u'/camps/%s/(\d+)/' % unicode(thisyear),  request.path)
    if m is not None:
        request_path = u'/thisyear/%s/' % m.groups()[0]
    else:
        request_path = request.path

    for l in links:
        l.title = standard_subs(l.title)
        l.isCurrentPage = False
        l.isCurrentSection = False
        if l.url == request_path:
            l.isCurrentPage = True
        elif request_path.startswith(l.url) and l.url != u'/':
            l.isCurrentSection = True

    context['menulinks'] = links
    context['GOOGLE_ANALYTICS_ACCOUNT'] = getattr(settings, 'GOOGLE_ANALYTICS_ACCOUNT', '')

    return context


member_username_re = re.compile(r'^[A-Za-z0-9_]{3,15}$')

def get_member_href(user_name):
    if not member_username_re.match(user_name):
        # This can get called from feeds, and we need to ensure
        # we don't generate a URL, as it will go nowhere (also causes problems
        # with the feed framework and utf-8).
        # Also, this can be called via bbcode, so we need to ensure
        # that we don't pass anything to urlresolvers.reverse that
        # will make it die.
        return u''
    else:
        return reverse('cciwmain.members.detail', kwargs={'user_name':user_name})


def get_member_link(user_name):
    user_name = user_name.strip()
    if user_name.startswith(u"'"):
        return user_name
    else:
        return mark_safe(u'<a title="Information about user \'%s\'" href="%s">%s</a>' % \
               (user_name, get_member_href(user_name), user_name))


def get_current_domain():
    return Site.objects.get_current().domain


from cciw.cciwmain import feeds
