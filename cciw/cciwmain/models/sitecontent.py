from django.db import models
from django.contrib.admin.views.main import quote
from django.utils.safestring import mark_safe
import cciw.cciwmain.common
import cciw.middleware.threadlocals as threadlocals

class MenuLink(models.Model):
    title = models.CharField("title", max_length=50)
    url = models.CharField("URL", max_length=100)
    extra_title = models.CharField("Disambiguation title", max_length=100, blank=True)
    listorder = models.SmallIntegerField("order in list")
    visible = models.BooleanField("Visible", default=True)
    parent_item = models.ForeignKey("self", null=True, blank=True,
        verbose_name="Parent item (none = top level)",
        related_name="child_links")

    def __unicode__(self):
        from cciw.cciwmain.common import standard_subs
        return  u"%s [%s]" % (self.url, standard_subs(self.title))
    
    def get_visible_children(self, request):
        """Gets a list of child menu links that should be visible given the current url"""
        if request.path == self.url:
            return self.child_links
        else:
            return []
    
    class Meta:
        app_label = "cciwmain"
        ordering = ('listorder','parent_item')
        #order_with_respect_to = 'parent_item' # doesn't seem to work
        
    class Admin:
        list_display = ('title', 'url', 'listorder','visible','parent_item')

class HtmlChunk(models.Model):
    name = models.SlugField("name", primary_key=True, db_index=True)
    html = models.TextField("HTML")
    menu_link = models.ForeignKey(MenuLink, verbose_name="Associated URL",
        null=True, blank=True)
    page_title = models.CharField("page title (for chunks that are pages)", max_length=100,
        blank=True)
    
    def __unicode__(self):
        return self.name
        
    def render(self, request):
        """Render the HTML chunk as HTML, with replacements
        made and any member specific adjustments."""
        html = cciw.cciwmain.common.standard_subs(self.html)
        user = threadlocals.get_current_user()
        if user and not user.is_anonymous() and user.is_staff \
            and user.has_perm('cciwmain.change_htmlchunk'):
            html += (u"""<div class="editChunkLink">&laquo;
                        <a href="/admin/cciwmain/htmlchunk/%s/">Edit %s</a> &raquo;
                        </div>""" % (quote(self.name), self.name))
        return mark_safe(html)

    class Meta:
        app_label = "cciwmain"   
        verbose_name = "HTML chunk"

    class Admin:
        list_display = ('name', 'page_title', 'menu_link')
       
