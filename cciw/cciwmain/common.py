"""
Utility functions and base classes that are common to all views etc.
"""
from functools import update_wrapper
import re
import sys
import traceback

from django.conf import settings
from django.core.mail import mail_admins
from django.core.paginator import Paginator, InvalidPage
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import classonlymethod
from django.utils.safestring import mark_safe

from cciw.cciwmain.utils import python_to_json
import cciw.middleware.threadlocals as threadlocals


# Our own CBV base class. Only the stuff we really need.
# Subclasses must implement 'handle'.

class View(object):

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classonlymethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.context = {}
            if hasattr(self, 'pre_handle'):
                response = self.pre_handle(request, *args, **kwargs)
                if response is not None:
                    return response
            return self.handle(request, *args, **kwargs)
        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from 'handle'
        update_wrapper(view, cls.handle, assigned=())
        return view


class TemplateView(View):
    """
    View that provides utilities to render to an HTML template,
    with utilities for collecting context data.
    """
    template_name = None
    response_class = TemplateResponse
    content_type = "text/html"

    def get_magic_context(self):
        """
        Collects any 'magic_context' defined in classes or base classes, and
        adds all to context data.

        (It's 'magic'' because a subclass definition of 'magic_context' doesn't
        override the superclass, but effectively adds to it, making it easy to
        add extra data without explicit 'super' or dictionary merging.')

        """
        context = {}
        for cls in reversed(self.__class__.mro()):
            if hasattr(cls, 'magic_context'):
                magic_context = cls.magic_context
                if callable(magic_context):
                    magic_context = magic_context(self)
                context.update(magic_context)
        return context

    def get_context_data(self, request):
        # Magic context from classes
        c = self.get_magic_context()
        # Add in 'context' from instance
        c.update(getattr(self, 'context', {}))
        return c

    def render(self, view_context):
        request = self.request
        assert self.template_name is not None
        context = self.get_context_data(request)
        context.update(view_context)
        response_kwargs = {}
        response_kwargs.setdefault('content_type', self.content_type)
        return self.response_class(
            request=request,
            template=[self.template_name],
            context=context,
        )

    def handle(self, request):
        return self.render({})


class CciwBaseView(TemplateView):
    metadata_title = None
    metadata_description = None
    metadata_keywords = None

    def get_context_data(self, request):
        d = dict(title=self.metadata_title,
                 description=self.metadata_description,
                 keywords=self.metadata_keywords)
        c = super(CciwBaseView, self).get_context_data(request)
        d.update(c)
        return d


class AjaxFormValidation(object):
    """
    A mixin that enables the returning of validation results by JSON
    if accessed with ?format=json.
    """
    def pre_handle(self, request, *args, **kwargs):
        if request.method == "POST":
            if request.GET.get('format', None) == 'json':
                form = self.form_class(request.POST)
                return HttpResponse(
                    python_to_json(form.errors),
                    content_type='text/javascript',
                )


class DetailView(object):
    def handle(self, request, slug=None):
        assert hasattr(self, 'slug_field'), "DetailView class must define slug_field (model lookup name)"
        assert hasattr(self, 'object_name'), "DetailView class must define object_name (name to be used in template)"
        assert hasattr(self, 'queryset'), "DetailView class must define queryset"
        kwargs = {self.slug_field + "__exact": slug}
        model = self.queryset.model
        try:
            obj = self.queryset.get(**kwargs)
        except model.DoesNotExist:
            raise Http404
        return self.render({self.object_name: obj})


class ListView(object):
    def get_queryset(self):
        assert hasattr(self, 'queryset'), "ListView class must define queryset, or override get_queryset"
        return self.queryset

    def handle(self, request):
        assert hasattr(self, 'list_name'), "ListView class must define list_name (name to be used in template)"
        queryset = self.get_queryset()
        paginate_by = getattr(self, 'paginate_by', None)
        return object_list(
            request,
            template_name=self.template_name,
            paginate_by=paginate_by,
            queryset=queryset,
            list_name=self.list_name,
            extra_context=self.get_context_data(request),
        )


def json_validation_request(request, form):
    """
    Returns a JSON validation response for a form, if the request is for JSON
    validation.
    """

    if request.GET.get('format') == 'json':
        return HttpResponse(python_to_json(form.errors),
                            content_type='text/javascript')
    else:
        return None


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

    def pre_handle(self, request, *args, **kwargs):
        if self.is_feed_request():
            feed_class = self.get_feed_class()
            return feeds.handle_feed_request(self.request, feed_class, self.get_queryset())


def object_list(request, queryset, extra_context=None,
                template_name='', paginate_by=None,
                list_name='object_list',
                ):
        if paginate_by:
            paginator = Paginator(queryset, paginate_by, orphans=0,
                                  allow_empty_first_page=True)

            page = request.GET.get('page') or 1
            try:
                page_number = int(page)
            except ValueError:
                if page == 'last':
                    page_number = paginator.num_pages
                else:
                    raise Http404("Page is not 'last', nor can it be converted to an int.")

            try:
                page = paginator.page(page_number)
            except InvalidPage as e:
                raise Http404('Invalid page (%(page_number)s): %(message)s' % {
                    'page_number': page_number,
                    'message': str(e)
                })
            context = {
                'paginator': paginator,
                'page_obj': page,
                'is_paginated': page.has_other_pages(),
                list_name: page.object_list,
            }
        else:
            context = {
                'paginator': None,
                'page_obj': None,
                'is_paginated': False,
                list_name: queryset,
            }
        context.update(extra_context)
        return TemplateResponse(
            request=request,
            template=[template_name],
            context=context,
        )


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
        or (timezone.now() - _thisyear_timestamp).seconds > 3600:
        from cciw.cciwmain.models import Camp
        try:
            lastcamp = Camp.objects.prefetch_related(None).order_by('-end_date')[0]
        except IndexError:
            return timezone.now().year
        if lastcamp.is_past():
            _thisyear = lastcamp.year + 1
        else:
            _thisyear = lastcamp.year
        _thisyear_timestamp = timezone.now()
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
    return mark_safe(u" :: ".join(map(str, links)))


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
    assert type(request.path) is str
    context['homepage'] = (request.path == u"/")

    # Ugly special casing for 'thisyear' camps
    m = re.match(u'/camps/%s/(\d+)/' % str(thisyear),  request.path)
    if m is not None:
        request_path = u'/thisyear/%s/' % m.groups()[0]
    else:
        request_path = request.path

    # As a callable, get_links will get called automatically by the template
    # renderer *when needed*, so we avoid queries. We memoize in links_cache to
    # avoid double queries
    links_cache = []
    def get_links():
        if len(links_cache) > 0:
            return links_cache
        else:
            for l in MenuLink.objects.filter(parent_item__isnull=True, visible=True):
                l.title = standard_subs(l.title)
                l.isCurrentPage = False
                l.isCurrentSection = False
                if l.url == request_path:
                    l.isCurrentPage = True
                elif request_path.startswith(l.url) and l.url != u'/':
                    l.isCurrentSection = True
                links_cache.append(l)
            return links_cache

    context['menulinks'] = get_links
    context['GOOGLE_ANALYTICS_ACCOUNT'] = getattr(settings, 'GOOGLE_ANALYTICS_ACCOUNT', '')
    context['PRODUCTION'] = (settings.LIVEBOX and settings.PRODUCTION)

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


def exception_notify_admins(subject):
    """
    Send admins notification of an exception that occurred
    """
    exc_info = sys.exc_info()
    message = '\n'.join(traceback.format_exception(*exc_info))
    mail_admins(subject, message, fail_silently=True)


from cciw.cciwmain import feeds
