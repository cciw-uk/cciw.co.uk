import copy

from django.contrib import admin
from django.contrib.admin import widgets as admin_widgets
from django.db.models.fields import Field
from django.forms.fields import Field as FormField
from django.http import HttpRequest
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html

from .fields import DocumentField


class DocumentRelatedModelAdminMixin:
    """
    Add this to any ModelAdmin needing to function with DocumentField.
    """

    formfield_overrides = {
        DocumentField: {"widget": admin_widgets.AdminFileWidget},
    }

    def formfield_for_dbfield(self, db_field: Field, request: HttpRequest, **kwargs) -> FormField:
        # This stops BaseModelAdmin from doing its custom ForeignKey handling,
        # which breaks for us because we are returning very different
        # form fields and widgets.
        if isinstance(db_field, DocumentField):
            klass = db_field.__class__
            kwargs = {**copy.deepcopy(self.formfield_overrides[klass]), **kwargs}
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class DocumentAdmin(admin.ModelAdmin):
    # Use this as a base class for ModelAdmin for Document subclasses
    search_fields = ["filename"]

    @admin.display(ordering="filename")
    def filename(document):
        return format_html("<a href={0}>{1}</a>", document.url, document.filename)

    @admin.display(ordering="size")
    def size(document):
        return filesizeformat(document.size)

    @admin.display(ordering="filename")
    def download(document):
        return document.download_link

    list_display = ["filename", size, "created_at", download]
    list_display_links = []

    fields = ["filename", "size", "created_at"]
    readonly_fields = fields
