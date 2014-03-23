from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe

from cciw.cciwmain.common import standard_subs
import cciw.middleware.threadlocals as threadlocals


@python_2_unicode_compatible
class MenuLink(models.Model):
    title = models.CharField("title", max_length=50)
    url = models.CharField("URL", max_length=100)
    extra_title = models.CharField("Disambiguation title", max_length=100, blank=True)
    listorder = models.SmallIntegerField("order in list")
    visible = models.BooleanField("Visible", default=True)
    parent_item = models.ForeignKey("self", null=True, blank=True,
        verbose_name="Parent item (none = top level)",
        related_name="child_links")

    def __str__(self):
        return  u"%s [%s]" % (self.url, standard_subs(self.title))

    def get_visible_children(self, request):
        """Gets a list of child menu links that should be visible given the current url"""
        if request.path == self.url:
            return self.child_links
        else:
            return []

    class Meta:
        # put top level items at top of list, others into groups, for the admin
        ordering = ('-parent_item__id', 'listorder')


@python_2_unicode_compatible
class HtmlChunk(models.Model):
    name = models.SlugField("name", primary_key=True, db_index=True)
    html = models.TextField("HTML")
    menu_link = models.ForeignKey(MenuLink, verbose_name="Associated URL",
        null=True, blank=True)
    page_title = models.CharField("page title (for chunks that are pages)", max_length=100,
        blank=True)

    def __str__(self):
        return self.name

    def render(self, request):
        """Render the HTML chunk as HTML, with replacements
        made and any member specific adjustments."""
        html = standard_subs(self.html)
        user = threadlocals.get_current_user()
        if user and not user.is_anonymous() and user.is_staff \
            and user.has_perm('sitecontent.change_htmlchunk'):
            html += (u"""<div class="editChunkLink">&laquo;
                        <a href="%s">Edit %s</a> &raquo;
                        </div>""" % (reverse("admin:sitecontent_htmlchunk_change", args=[self.name]),
                                     self.name))
        return mark_safe(html)

    class Meta:
        verbose_name = "HTML chunk"
