from django.core import template
from django.utils import html
from cciw.apps.cciw.settings import *
from cciw.apps.cciw.utils import *

def page_link(request, page_number):
	"""Constructs a link to a specific page using the request.  Returns HTML escaped value"""
	return html.escape(modified_query_string(request, {'page': str(page_number)}))

class PagingControlNode(template.Node):
	def render(self, context):
		# context has been populated by
		# generic view paging mechanism
		cur_page = int(context['page'])-1
		total_pages = int(context['pages'])
		request = context['pagevars'].request
		output = ''		
		if (total_pages > 1):
			output += "[Page " + str(cur_page+1) + " of " + str(total_pages)+ "]&nbsp;&nbsp; "
			for i in range(0, total_pages):
				if (i > 0):
					output += " | "
				if i == cur_page:
					output += '<span class="pagingLinkCurrent">' + str(i+1) + '</span>'
				else:
					output += '<a class="pagingLink" href="' + page_link(request, i)+ '">' + str(i+1) + '</a>'
			output += " | "
			if cur_page > 0:
				output += '<a class="pagingLink" title="Previous page" href="' + page_link(request, cur_page - 1) + '">&laquo;</a>'
			else:
				output += '<span class="pagingLinkCurrent">&laquo;</span>'
			output += "&nbsp;"
			if cur_page < total_pages - 1:
				output += '<a class="pagingLink" title="Next page" href="' + page_link(request, cur_page + 1) + '">&raquo;</a>'
			else:
				output += '<span class="pagingLinkCurrent">&raquo;</span>'
		return output
		

def do_paging_control(parser, token):
	"""
	Creates a list of links to the pages of a generic view.
	The paging  control requires that the request object be in the context as 
	by putting the standard 'pagevars' object in the context.
	
	Usage::

		{% paging_control %}

"""
	return PagingControlNode()

class SortingControlNode(template.Node):
	def __init__(self, ascending_param, descending_param):
		self.ascending_param = ascending_param
		self.descending_param = descending_param
	
	def render(self, context):
		request = context['pagevars'].request
		output = '<span class="sortingControl">'
		current_order = request.GET.get('order','')
		if current_order == '':
			try:
				current_order = context['default_order']
			except KeyError:
				current_order = ''
			
		if current_order == self.ascending_param:
			output += '<a href="' + html.escape(modified_query_string(request, {'order': self.descending_param})) + '">' + \
			'<img class="sortAscActive" src="' + CCIW_MEDIA_ROOT + 'images/arrow-up.gif" alt="Sorted ascending" /></a>' 
		elif current_order == self.descending_param:
			output += '<a href="' + html.escape(modified_query_string(request, {'order': self.ascending_param})) + '">' + \
			'<img class="sortDescActive" src="' + CCIW_MEDIA_ROOT + 'images/arrow-down.gif" width="10" alt="Sorted descending" /></a>'
		else:
			# query string resets page to zero if we use a new type of sorting
			output += '<a href="' + html.escape(modified_query_string(request, {'order': self.ascending_param, 'page': 0})) + '">' + \
			'<img class="sortAsc" src="' + CCIW_MEDIA_ROOT + 'images/arrow-up.gif" alt="Sort ascending" /></a>'
		
		output += '</span>'
		return output
		

def do_sorting_control(parser, token):
	"""
	Creates a pair of links that are used for sorting a list on a field.
	Two parameters are accepted, which must be the query string parameter values that should
	be used for ascending and descending sorts on a field.
	
	The query string parameter name is always 'order', and the view function
	will need to check that parameter and adjust accordingly.  The view function
	should also add 'default_order' to the context, which allows the 
	sorting control to determine what the current sort order is if no
	'order' parameter exists in the query string.
	
	The sorting control requires that the request object be in the context as 
	by putting the standard 'pagevars' object in the context. It is
	used for various things, including passing on other query string parameters
	in the generated URLs
	
	
	Usage::
	
		{% sorting_control "ad" "dd" %}
		
	This might be used for 'date ascending' and 'date descending' order
	"""
	try:
		tag_name, ascending_param, descending_param = token.contents.split(None, 2)
	except ValueError:
		raise template.TemplateSyntaxError, "sorting_control tag requires two arguments"
	ascending_param = ascending_param.strip('"')
	descending_param = descending_param.strip('"')
	return SortingControlNode(ascending_param, descending_param)

class ForwardQueryParamNode(template.Node):
	def __init__(self, param_name):
		self.param_name = param_name

	def render(self, context):
		# requires the standard extra context
		request = context['pagevars'].request
		return '<div><input type="hidden" name="' + self.param_name + \
			'" value="' + html.escape(request.GET.get(self.param_name, '')) + '" /></div>'
		
# forward_query_param - turn a param in query string into a hidden
# input field.  Needs to be able to get the request object from the context
def do_forward_query_param(parser, token):
	"""
	Turns a parameter in a query string into a hidden input field,
	allowing it to be 'forwarded' as part of the next request in
	a form submission.  It requires one argument (the name of the control),
	and also requires that the request object be in the context as 
	by putting the standard 'pagevars' object in the context.
	"""
	try:
		tag_name, param_name = token.contents.split(None, 1)
	except ValueError:
		raise template.TemplateSyntaxError, "forward_query_param tag requires an arguments"
	param_name = param_name.strip('"')
	return ForwardQueryParamNode(param_name)
	
template.register_tag('paging_control', do_paging_control)
template.register_tag('sorting_control', do_sorting_control)
template.register_tag('forward_query_param', do_forward_query_param)
