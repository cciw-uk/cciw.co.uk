from django.contrib.admin.utils import quote
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from cciw.cciwmain.common import standard_subs
import cciw.middleware.threadlocals as threadlocals


class MenuLink(models.Model):
    title = models.CharField("title", max_length=50)
    url = models.CharField("URL", max_length=100)
    extra_title = models.CharField("Disambiguation title", max_length=100, blank=True)
    listorder = models.SmallIntegerField("order in list")
    visible = models.BooleanField("Visible", default=True)
    parent_item = models.ForeignKey("self", null=True, blank=True,
                                    on_delete=models.CASCADE,
                                    verbose_name="Parent item (none = top level)",
                                    related_name="child_links")

    def __str__(self):
        return "%s [%s]" % (self.url, standard_subs(self.title))

    def get_visible_children(self, request):
        """Gets a list of child menu links that should be visible given the current url"""
        if request.path == self.url:
            return self.child_links
        else:
            return []

    class Meta:
        # put top level items at top of list, others into groups, for the admin
        ordering = ('-parent_item__id', 'listorder')


class HtmlChunk(models.Model):
    name = models.SlugField("name", primary_key=True, db_index=True)
    html = models.TextField("HTML")
    menu_link = models.ForeignKey(MenuLink,
                                  on_delete=models.CASCADE,
                                  verbose_name="Associated URL",
                                  null=True, blank=True)
    page_title = models.CharField("page title (for chunks that are pages)", max_length=100,
                                  blank=True)

    def __str__(self):
        return self.name

    def render(self, request):
        """Render the HTML chunk as HTML, with replacements
        made and any member specific adjustments."""
        html = mark_safe(standard_subs(self.html))
        user = threadlocals.get_current_user()
        if (user and not user.is_anonymous() and user.is_staff and
                user.has_perm('sitecontent.change_htmlchunk')):
            html += format_html("""<div class="editChunkLink">&laquo;
                                <a href="{0}">Edit {1}</a> &raquo;
                                </div>""",
                                reverse("admin:sitecontent_htmlchunk_change", args=(quote(self.name),)),
                                self.name)
        return html

    class Meta:
        verbose_name = "HTML chunk"
