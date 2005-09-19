from django.core.extensions import DjangoContext
from django.models.sitecontent import *
from django.models.members import members
from cciw.apps.cciw.settings import *
from datetime import datetime

class PageVars:
	"""Stores general data to be used be the 'standard' template"""
	def __init__(self, request, title):
		self.title = title
		self.mediaRootUrl = CCIW_MEDIA_ROOT
		self.styleSheetUrl = self.mediaRootUrl + 'style.css'
		self.request = request


class StandardContext(DjangoContext):
	"""Provides simple construction of context needed for the 'standard.html' template and
	templates that inherit from it"""
	def __init__(self, request, dict=None, title=None):
		if dict is None: dict = {}
		# modify the context dictionary, then construct the base class
		dict = standard_extra_context(request, dict, title)
		DjangoContext.__init__(self, request, dict)
		
def standard_extra_context(request, dict=None, title=None):
	"""Can be used directly to get an extra context dictionary e.g. for generic views.  Normally use via StandardContext"""
	if dict is None: dict = {}
	if title is None:
		title = "Christian Camps in Wales"
	dict['pagevars'] = PageVars(request, title)
	dict['thisyear'] = THISYEAR
	
	member = get_current_member(request)
	if not member is None:
		dict['currentMember'] = member
		

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
		
	dict['menulinks'] = links
	return dict

def get_current_member(request):
	try:
		member = members.get_object(id__exact = request.session['member_id'])
		# use opportunity to update lastSeen data
		member.lastSeen = datetime.now()
		member.save()
		return member
	except KeyError, members.MemberDoesNotExist:
		return None

def standard_subs(value):
	"""Standard substitutions made on HTML content"""
	return value.replace('{{thisyear}}', str(THISYEAR)).replace('{{media}}', CCIW_MEDIA_ROOT)
	

def slugify(value):
    "Converts to lowercase, removes non-alpha chars and converts spaces to hyphens"
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('\s+', '-', value)




	
