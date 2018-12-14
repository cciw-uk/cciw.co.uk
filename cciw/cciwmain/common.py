"""
Utility functions and base classes that are common to all views etc.
"""
import re
import sys
import traceback
from datetime import date, timedelta
from functools import update_wrapper

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import mail_admins
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import classonlymethod
from django.utils.html import format_html_join
from frozendict import frozendict

from cciw.cciwmain.utils import python_to_json


# Our own CBV base class. Only the stuff we really need.
# Subclasses must implement 'handle'.
# See - https://lukeplant.me.uk/blog/posts/my-approach-to-class-based-views/
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


class TemplateMeta(type):
    def __new__(cls, name, bases, namespace):
        m_c = namespace.get('magic_context', None)
        if m_c is not None and not callable(m_c):
            # Make sure it is immutable, to prevent accidental changes by
            # methods.
            namespace['magic_context'] = frozendict(m_c)
        return type.__new__(cls, name, bases, namespace)


class TemplateView(View, metaclass=TemplateMeta):
    """
    View that provides utilities to render to an HTML template,
    with utilities for collecting context data.
    """
    template_name = None
    response_class = TemplateResponse
    content_type = "text/html"

    def __init__(self, **kwargs):
        super(TemplateView, self).__init__(**kwargs)
        self.context = {}

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

    magic_context = lambda self: dict(title=self.metadata_title,
                                      description=self.metadata_description,
                                      keywords=self.metadata_keywords)


class AjaxFormValidation(object):
    """
    A mixin that enables the returning of validation results by JSON
    if accessed with ?format=json.
    """
    ajax_form_validation_skip_fields = []

    def pre_handle(self, request, *args, **kwargs):
        if request.method == "POST":
            if request.GET.get('format', None) == 'json':
                data = request.POST.copy()
                # Don't validate skipped fields
                for f in self.ajax_form_validation_skip_fields:
                    data.pop(f)
                form = self.form_class(data)
                errors = form.errors.copy()
                # And don't report their errors either
                for f in self.ajax_form_validation_skip_fields:
                    errors.pop(f)
                return HttpResponse(
                    python_to_json(errors),
                    content_type='text/javascript',
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


_thisyear = None
_thisyear_timestamp = None


def get_thisyear():
    """
    Get the year the website is currently on.  The website year is
    equal to the year of the last camp in the database, or the year
    afterwards if that camp is at least 30 days in the past.
    (30 days, to give a leaders the chance to access the leader
    area after their camp is finished).
    """
    global _thisyear, _thisyear_timestamp
    if (_thisyear is None or _thisyear_timestamp is None or
            (timezone.now() - _thisyear_timestamp).seconds > 3600):
        from cciw.cciwmain.models import Camp
        try:
            lastcamp = Camp.objects.prefetch_related(None).order_by('-end_date')[0]
        except IndexError:
            return timezone.now().year
        if lastcamp.end_date + timedelta(days=30) <= date.today():
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
standard_subs.is_safe = True  # noqa:305 provided our substitutions don't introduce anything that must be escaped


def create_breadcrumb(links):
    return format_html_join(" :: ", "{0}", ((l,) for l in links))


def standard_processor(request):
    """
    Processor that does standard processing of request that we need for all
    pages.
    """
    context = {}
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
    context['homepage'] = (request.path == "/")

    # Ugly special casing for 'thisyear' camps
    m = re.match('/camps/%s/(\d+)/' % str(thisyear), request.path)
    if m is not None:
        request_path = '/thisyear/%s/' % m.groups()[0]
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
                l.is_current_page = False
                l.is_current_section = False
                if l.url == request_path:
                    l.is_current_page = True
                elif request_path.startswith(l.url) and l.url != '/':
                    l.is_current_section = True
                links_cache.append(l)
            return links_cache

    context['menulinks'] = get_links
    context['GOOGLE_ANALYTICS_ACCOUNT'] = getattr(settings, 'GOOGLE_ANALYTICS_ACCOUNT', '')
    context['PRODUCTION'] = settings.LIVEBOX

    return context


def get_current_domain():
    return Site.objects.get_current().domain


def exception_notify_admins(subject):
    """
    Send admins notification of an exception that occurred
    """
    exc_info = sys.exc_info()
    message = '\n'.join(traceback.format_exception(*exc_info))
    mail_admins(subject, message, fail_silently=True)
