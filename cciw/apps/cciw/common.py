from django.core.extensions import DjangoContext

class Page:
	"""Stores general data to be used be the standard template"""
	def __init__(self, request, title):
		self.request = request
		self.title = title
		self.mediaRootUrl = 'http://cciw_django_local'
		self.styleSheetUrl = self.mediaRootUrl + '/media/style.css'

class StandardContext(DjangoContext):
	"""Provides simple construction of context needed for the 'standard.html' template and
	templates that inherit from it"""
	def __init__(self, request, dict={}, title=None):
		# modify the context dictionary, then construct the base class
		if title == None:
			title = "Christian Camps in Wales"
		dict['page'] = Page(request, title)
		DjangoContext.__init__(self, request, dict)

def slugify(value):
    "Converts to lowercase, removes non-alpha chars and converts spaces to hyphens"
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('\s+', '-', value)

