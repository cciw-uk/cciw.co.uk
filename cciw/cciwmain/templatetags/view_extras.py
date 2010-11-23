from django import template
from django.utils import html
from django.conf import settings
from cciw.cciwmain.utils import *

def page_link(request, page_number, fragment = ''):
    """
    Constructs a link to a specific page using the request.
    Returns HTML escaped value
    """
    return html.escape(modified_query_string(request, {'page': unicode(page_number)}, fragment))

class PagingControlNode(template.Node):
    def __init__(self, fragment = ''):
        self.fragment = fragment

    def render(self, context):
        # context has been populated by
        # generic view paging mechanism
        cur_page = int(context['page'])
        total_pages = int(context['pages'])
        request = context['request']

        output = []
        if (total_pages > 1):
            output.append(u"&mdash; Page %d  of %d &mdash;&nbsp;&nbsp; " %
                (cur_page, total_pages))

            # Constraints:
            # - Always have: first page, last page, next page, previous page
            # - Never have more than about 10 links
            # - Have links spread out through range e.g. if 100 pages,
            #    show links at 10 page intervals.

            # Initial set
            pages = set(p for p in range(cur_page - 2, cur_page + 3)
                            if p >= 1 and p <= total_pages)
            pages.add(1)
            pages.add(total_pages)

            # Add some more at intervals
            # Ensure that if we are using ellipses, we don't
            # get any adjacent numbers since that looks odd.
            interval = max(float(total_pages/8.0), 2)
            for i in xrange(1, 9):
                p = int(i * interval)
                if p <= total_pages:
                    pages.add(p)

            last_page = 0
            for i in sorted(pages):
                if (i > 0):
                    output.append(u" ")
                if i > last_page + 1:
                    output.append(u"&hellip; ")

                if i == cur_page:
                    output.append(u'<span class="pagingLinkCurrent">%s</span>' % unicode(i))
                else:
                    output.append(
                        u'<a title="%(title)s" class="pagingLink" href="%(href)s">%(pagenumber)d</a>' % \
                        { 'title': u'Page ' + unicode(i),
                          'href': page_link(request, i, self.fragment),
                          'pagenumber': i })
                last_page = i
            output.append(" | ")
            if cur_page > 1:
                output.append(
                    u'<a class="pagingLink" title="Previous page" href="%s">&laquo;</a>' % \
                    page_link(request, cur_page - 1, self.fragment))
            else:
                output.append(u'<span class="pagingLinkCurrent">&laquo;</span>')
            output.append(u"&nbsp;")
            if cur_page < total_pages:
                output.append(
                    u'<a class="pagingLink" title="Next page" href="%s">&raquo;</a>' % \
                    page_link(request, cur_page + 1, self.fragment))
            else:
                output.append(u'<span class="pagingLinkCurrent">&raquo;</span>')
        return u''.join(output)



def do_paging_control(parser, token):
    """
    Creates a list of links to the pages of a generic view. The paging control
    requires that the request object be in the context as 'request'

    An optional parameter can be used which contains the fragment to use for
    paging links, which allows paging to skip any initial common content on the page.

    Usage::

        {% paging_control %}

"""
    parts = token.contents.split(None, 1)
    if len(parts) > 1:
        return PagingControlNode(fragment=parts[1])
    else:
        return PagingControlNode()

class EarlierLaterNode(template.Node):
    def render(self, context):
        cur_page = int(context['page'])
        total_pages = int(context['pages'])
        request = context['request']
        output = [u'<span class="earlierlater">']
        if cur_page < total_pages:
            output.append(u'<a href="%s">&laquo; earlier</a>' % page_link(request, cur_page + 1))
        else:
            output.append(u'&laquo; earlier')
        output.append(' | ')
        if cur_page > 1:
            output.append(u'<a href="%s">later &raquo;</a>' % page_link(request, cur_page - 1))
        else:
            output.append(u'later &raquo;')
        output.append(u'</span>')
        return ''.join(output)

def do_ealier_later(parser, token):
    return EarlierLaterNode()

class SortingControlNode(template.Node):
    def __init__(self, ascending_param, descending_param,
                 ascending_title, descending_title):
        self.ascending_param = ascending_param
        self.descending_param = descending_param
        self.ascending_title = ascending_title
        self.descending_title = descending_title

    def render(self, context):
        request = context['request']
        output = u'<span class="sortingControl">'
        current_order = request.GET.get('order','')
        if current_order == u'':
            try:
                current_order = context['default_order']
            except KeyError:
                current_order = u''

        if current_order == self.ascending_param:
            output += u'<a title="%s" href="%s">' % (self.descending_title, html.escape(modified_query_string(request, {'order': self.descending_param}))) + \
                u'<img class="sortAscActive" src="%simages/arrow-up.gif" alt="Sorted ascending" /></a>' % settings.STATIC_URL
        elif current_order == self.descending_param:
            output += u'<a title="%s" href="%s">' % (self.ascending_title, html.escape(modified_query_string(request, {'order': self.ascending_param}))) + \
                u'<img class="sortDescActive" src="%simages/arrow-down.gif" alt="Sorted descending" /></a>' % settings.STATIC_URL
        else:
            # query string resets page to zero if we use a new type of sorting
            output += u'<a title="%s" href="%s">' % (self.ascending_title, html.escape(modified_query_string(request, {'order': self.ascending_param, 'page': 1}))) + \
                u'<img class="sortAsc" src="%simages/arrow-up.gif" alt="Sort ascending" /></a>' % settings.STATIC_URL

        output += u'</span>'
        return output


def do_sorting_control(parser, token):
    """
    Creates a pair of links that are used for sorting a list on a field.
    Four parameters are accepted, which must be the query string parameter values that
    should be used for ascending and descending sorts on a field, and the corresponding
    title text for those links (in that order). All arguments must be quoted with '"'

    The query string parameter name is always 'order', and the view function
    will need to check that parameter and adjust accordingly.  The view function
    should also add 'default_order' to the context, which allows the
    sorting control to determine what the current sort order is if no
    'order' parameter exists in the query string.

    The sorting control requires that the request object be in the context
    as 'request'. (It is used for various things, including passing on
    other query string parameters in the generated URLs.)

    Usage::

        {% sorting_control "ad" "dd" "Sort date ascending" "Sort date descending" %}

    """
    bits = token.contents.split('"')
    if len(bits) != 9:
        raise template.TemplateSyntaxError, "sorting_control tag requires 4 quoted arguments"
    return SortingControlNode(bits[1].strip('"'), bits[3].strip('"'),
                              bits[5].strip('"'), bits[7].strip('"'),)

class ForwardQueryParamNode(template.Node):
    def __init__(self, param_name):
        self.param_name = param_name

    def render(self, context):
        request = context['request']
        return u'<div><input type="hidden" name="%s" value="%s" /></div>' % \
               (self.param_name, html.escape(request.GET.get(self.param_name, '')))


# forward_query_param - turn a param in query string into a hidden
# input field.  Needs to be able to get the request object from the context
def do_forward_query_param(parser, token):
    """
    Turns a parameter in a query string into a hidden input field,
    allowing it to be 'forwarded' as part of the next request in
    a form submission.  It requires one argument (the name of the parameter),
    and also requires that the request object be in the context.
    """
    try:
        tag_name, param_name = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, \
            "forward_query_param tag requires an argument"
    param_name = param_name.strip('"')
    return ForwardQueryParamNode(param_name)

register = template.Library()
register.tag('paging_control', do_paging_control)
register.tag('earlier_later', do_ealier_later)
register.tag('sorting_control', do_sorting_control)
register.tag('forward_query_param', do_forward_query_param)
