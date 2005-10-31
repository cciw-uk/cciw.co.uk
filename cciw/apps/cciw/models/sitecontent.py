from django.core import meta

class MenuLink(meta.Model):
    title = meta.CharField("title", maxlength=50)
    url = meta.CharField("URL", maxlength=100)
    extra_title = meta.CharField("Disambiguation title", maxlength=100, blank=True)
    listorder = meta.SmallIntegerField("order in list")
    visible = meta.BooleanField("Visible", default=True)
    parent_item = meta.ForeignKey("self", null=True, blank=True,
        verbose_name="Parent item (none = top level)",
        related_name="child_link")

    def __repr__(self):
        from cciw.apps.cciw.common import standard_subs
        return self.url + " [" +  standard_subs(self.title) + "]"
    
    def get_visible_children(self, request):
        """Gets a list of child menu links that should be visible given the current url"""
        if request.path == self.url:
            return self.get_child_link_list()
        else:
            return []
    
    class META:
        admin = meta.Admin(
            list_display = ('title', 'url', 'listorder','visible','parent_item')
        )
        ordering = ('listorder','parent_item')
        #order_with_respect_to = 'parent_item' # doesn't seem to work
        
        

class HtmlChunk(meta.Model):
    name = meta.SlugField("name", db_index=True)
    html = meta.TextField("HTML")
    menu_link = meta.ForeignKey(MenuLink, verbose_name="Associated URL",
        null=True, blank=True)
    page_title = meta.CharField("page title (for chunks that are pages)", maxlength=100,
        blank=True)
    
    def __repr__(self):
        return self.name
        
    def render(self, context, context_var):
        """render the HTML chunk as if it were a Django template, 
        and store the result in a context object.
        
        The context parameter is used as the context for
        the rendering, and also to store the 
        result - in context[context_var]
        
        Also, if the context objectcontains a PageVars object, the  
        the HtmlChunk will be added to PageVars.html_chunks list
        
        """
        from django.core import template
        t = template.Template('{% load standardpage %}' + self.html)
        context[context_var] = t.render(context)
        #try:
        page_vars = context['pagevars']
        #except KeyError:
        #    page_vars = None
        #if page_vars is not None:
        page_vars.html_chunks.append(self)

    def _module_render_into_context(context, chunkdict):
        """Retrieve a set of HtmlChunks and render into the context object, chunks
        being defined as {contextvar: chunkname} in chunkdict"""
        # We use the context both for rendering the HtmlChunks,
        # and the destination context
        for context_var, chunkname in chunkdict.items():
            try:
                chunk = get_object(name__exact=chunkname)
                chunk.render(context, context_var)
            except HtmlChunkDoesNotExist:
                pass
        
    class META:
        admin = meta.Admin(
            list_display = ('name', 'page_title', 'menu_link')
        )
        verbose_name = "HTML chunk"


