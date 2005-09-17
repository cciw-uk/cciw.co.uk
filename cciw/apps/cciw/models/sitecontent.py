"Site Content"
from django.core import meta

class MenuLink(meta.Model):
	title = meta.CharField("title", maxlength=50)
	url = meta.CharField("URL", maxlength=100)
	extraTitle = meta.CharField("Disambiguation title", maxlength=100, blank=True)
	listorder = meta.SmallIntegerField("order in list")
	visible = meta.BooleanField("Visible", default=True)
	parentItem = meta.ForeignKey("self", null=True, blank=True,
		verbose_name="Parent item (none = top level)",
		related_name="childLink")

	def __repr__(self):
		return self.url + " [" + self.title + "]"
	
	def getVisibleChildren(self, request):
		"""Gets a list of child menu links that should be visible given the current url"""
		if request.path == self.url:
			return self.get_childLink_list()
		else:
			return []
	
	class META:
		admin = meta.Admin(
			list_display = ('title', 'url', 'listorder','visible','parentItem')
		)
		ordering = ('listorder','parentItem')
		#order_with_respect_to = 'parentItem' # doesn't seem to work
		
		

class HtmlChunk(meta.Model):
	name = meta.SlugField("name", db_index=True)
	html = meta.TextField("HTML")
	menuLink = meta.ForeignKey(MenuLink, verbose_name="Associated URL",
		null=True, blank=True)
	pageTitle = meta.CharField("page title (for chunks that are pages)", maxlength=100,
		blank=True)
	
	def __repr__(self):
		return self.name
		
	def render(self, context):
		"""render the HTML chunk as if it were a Django template"""
		from django.core import template
		t = template.Template('{% load standardpage %}' + self.html)
		return t.render(context)
	# render 1: using chunk as a django template

	def _module_renderIntoContext(context, chunkdict):
		"""Retrieve a set of HtmlChunks and render into the context object, chunks
		being defined as {contextvar: chunkname} in chunkdict"""
		# We use the context both for rendering the HtmlChunks,
		# and the destination context
		for contextvar, chunkname in chunkdict.items():
			try:
				chunktext = get_object(name__exact=chunkname)
				context[contextvar] = chunktext.render(context)
			except HtmlChunkDoesNotExist:
				pass
		
	class META:
		admin = meta.Admin()
		verbose_name = "HTML chunk"


