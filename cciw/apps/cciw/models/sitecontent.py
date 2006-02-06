from django.db import models

class MenuLink(models.Model):
    title = models.CharField("title", maxlength=50)
    url = models.CharField("URL", maxlength=100)
    extra_title = models.CharField("Disambiguation title", maxlength=100, blank=True)
    listorder = models.SmallIntegerField("order in list")
    visible = models.BooleanField("Visible", default=True)
    parent_item = models.ForeignKey("self", null=True, blank=True,
        verbose_name="Parent item (none = top level)",
        related_name="child_links")

    def __repr__(self):
        from cciw.apps.cciw.common import standard_subs
        return self.url + " [" +  standard_subs(self.title) + "]"
    
    def get_visible_children(self, request):
        """Gets a list of child menu links that should be visible given the current url"""
        if request.path == self.url:
            return self.child_links.all()
        else:
            return []
    
    class Meta:
        app_label = "cciw"
        ordering = ('listorder','parent_item')
        #order_with_respect_to = 'parent_item' # doesn't seem to work
        
    class Admin:
        list_display = ('title', 'url', 'listorder','visible','parent_item')

class HtmlChunk(models.Model):
    name = models.SlugField("name", primary_key=True, db_index=True)
    html = models.TextField("HTML")
    menu_link = models.ForeignKey(MenuLink, verbose_name="Associated URL",
        null=True, blank=True)
    page_title = models.CharField("page title (for chunks that are pages)", maxlength=100,
        blank=True)
    
    def __repr__(self):
        return self.name
        
    def render(self, context, context_var):
        """render the HTML chunk as if it were a Django template, 
        and store the result in a context object.
        
        The context parameter is used as the context for the rendering, 
        and also to store the result - in context[context_var]
        
        Also, if the context object contains a pagevars object, the  
        the HtmlChunk will be added to pagevars['html_chunks'] list
        
        """
        from django import template
        t = template.Template('{% load standardpage %}' + self.html)
        context[context_var] = t.render(context)

        hcl = context['html_chunk_list']
        if hcl == '':
            hcl = []
            
        context['html_chunk_list'] = hcl
        hcl.append(self)
        

    @staticmethod
    def render_into_context(context, chunkdict):
        """Retrieve a set of HtmlChunks and render into the context object, chunks
        being defined as {contextvar: chunkname} in chunkdict"""
        # We use the context both for rendering the HtmlChunks,
        # and the destination context
        for context_var, chunkname in chunkdict.items():
            try:
                chunk = HtmlChunk.objects.get(name=chunkname)
                chunk.render(context, context_var)
            except HtmlChunk.DoesNotExist:
                pass
        
    class Meta:
        app_label = "cciw"   
        verbose_name = "HTML chunk"

    class Admin:
        list_display = ('name', 'page_title', 'menu_link')
       
