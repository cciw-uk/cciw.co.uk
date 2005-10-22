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
        
    def render(self, context):
        """render the HTML chunk as if it were a Django template"""
        from django.core import template
        t = template.Template('{% load standardpage %}' + self.html)
        return t.render(context)
    # render 1: using chunk as a django template

    def _module_render_into_context(context, chunkdict):
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
        admin = meta.Admin(
            list_display = ('name', 'page_title', 'menu_link')
        )
        verbose_name = "HTML chunk"


