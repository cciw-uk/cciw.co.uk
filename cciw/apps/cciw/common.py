from django.core.extensions import DjangoContext
from django.models.sitecontent import *
from django.models.members import members
from cciw.apps.cciw.settings import *
import datetime

class PageVars:
	"""Stores general data to be used be the 'standard' template"""
	def __init__(self, request, title):
		self.title = title
		self.mediaRootUrl = CCIW_MEDIA_ROOT
		self.styleSheetUrl = self.mediaRootUrl + 'style.css'
		self.request = request
		self.loggedInMembers = members.get_count(lastSeen__gte = datetime.datetime.now() - datetime.timedelta(minutes=3))

class StandardContext(DjangoContext):
	"""Provides simple construction of context needed for the 'standard.html' template and
	templates that inherit from it"""
	def __init__(self, request, extra_dict=None, title=None):
		if extra_dict is None: extra_dict = {}
		# modify the context dictionary, then construct the base class
		extra_dict = standard_extra_context(request, extra_dict, title)
		DjangoContext.__init__(self, request, extra_dict)
		
def standard_extra_context(request, extra_dict=None, title=None):
	"""Can be used directly to get an extra context dictionary e.g. for generic views.  Normally use via StandardContext"""
	if extra_dict is None: extra_dict = {}
	if title is None:
		title = "Christian Camps in Wales"
	
	member = get_current_member(request)
	if not member is None:
		extra_dict['currentMember'] = member
		
	extra_dict['thisyear'] = THISYEAR
	extra_dict['pagevars'] = PageVars(request, title) # put this after get_current_member
		

	# TODO - filter on 'visible' attribute
	links = menulinks.get_list(where = ['parentItem_id IS NULL'])
	for l in links:
		l.title = standard_subs(l.title)
		l.isCurrentPage = False
		l.isCurrentSection = False
		if l.url == request.path:
			l.isCurrentPage = True
		elif request.path.startswith(l.url) and l.url != '/':
			l.isCurrentSection = True
		
	extra_dict['menulinks'] = links
	return extra_dict

def get_current_member(request):
	try:
		member = members.get_object(userName__exact = request.session['member_id'])
		# use opportunity to update lastSeen data
		if (datetime.datetime.now() - member.lastSeen).seconds > 60:
			member.lastSeen = datetime.datetime.now()
			member.save()
		return member
	except (KeyError, members.MemberDoesNotExist):
		return None

def standard_subs(value):
	"""Standard substitutions made on HTML content"""
	return value.replace('{{thisyear}}', str(THISYEAR)).replace('{{media}}', CCIW_MEDIA_ROOT)


def order_option_to_lookup_arg(order_options, lookup_args_dict, request, default_order_by):
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
	return "<div class='breadcrumb'>" + " :: ".join(links) + "</div>"
