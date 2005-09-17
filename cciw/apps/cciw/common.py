from django.core.extensions import DjangoContext
from django.models.sitecontent import *
from cciw.apps.cciw.settings import *

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
	def __init__(self, request, dict={}, title=None):
		# modify the context dictionary, then construct the base class
		dict = standard_extra_context(request, dict, title)
		DjangoContext.__init__(self, request, dict)
		
def standard_extra_context(request, dict={}, title=None):
	"""Can be used directly to get an extra context dictionary e.g. for generic views.  Normally use via StandardContext"""
	if title == None:
		title = "Christian Camps in Wales"
	dict['pagevars'] = PageVars(request, title)
	
	dict['thisyear'] = THISYEAR

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
		

def standard_subs(value):
	"""Standard substitutions made on HTML content"""
	return value.replace('{{thisyear}}', str(THISYEAR)).replace('{{media}}', CCIW_MEDIA_ROOT)
	

def slugify(value):
    "Converts to lowercase, removes non-alpha chars and converts spaces to hyphens"
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('\s+', '-', value)




	
