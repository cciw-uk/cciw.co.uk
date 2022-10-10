import io

from django.core.files.base import File
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

# This module is for storing documents/files in the database
#
# This in general is not a great pattern, but the disadvantages
# don't really apply to us:
#
# - we store small files,
# - and very few,
# - and they are rarely needed
# - and data retention policies on them mean we keep none long term,
#   and most for only a short period.

# The solution below is designed for our needs, including ensuring we know
# exactly where each file is from, and being able to apply different data
# retention policies based on the origin/use of document.

# Other solutions examined:
#
# * db-file-storage https://django-db-file-storage.readthedocs.io/
#
#   The provided views for downloading have no permissions applied, and in fact
#   allow queries against arbitrary database models - the request looks like:
#      /files/download/?name=app.ModelName%2Fbytes%2Ffilename%2Fmimetype%2Fthe_name.png
#
#   where app.ModelName etc. are not limited in any way, so the code will
#   execute queries against user-controlled tables. Upon examination, these
#   queries are not likely to succeed in extracting information, but it's not a
#   great start security-wise.
#
#   The backend also makes filenames unique across the model, and appends
#   random digits to make this so. This is unnecessary when we are storing
#   things in a DB, and we can do better than this.
#
#   It doesn't have referential integrity - no actual FKs to the model
#   that is storing data, just text reference.


class DocumentQuerySet(models.QuerySet):
    def older_than(self, before_datetime):
        return self.filter(created_at__lt=before_datetime)


class DocumentManager(models.Manager):
    def get_queryset(self):
        # defer content, so that we only get this potentially large
        # data when we really need it.
        # Remember to set `Meta.base_manager_name` when using this.
        return super().get_queryset().defer("content")


class Document(models.Model):
    """
    Abstract model for a document/file stored in the database.

    For example usage, see SupportingInformation and SupportingInformationDocument

    In short:
    - subclass Document e.g. MyDocument(Document)
    - use DocumentManager to create the default `objects` Manager on MyDocument.
      The main purpose is to defer loading of the `content` field.
    - create a OneToOne field to it from another model, using `DocumentField`
      e.g.
            class MyInfo(models.Model):
               document = DocumentField(MyDocument)

      The purpose of this model will vary. The DocumentField link may have
      `null=True` if the document is an optional part of MyInfo

    - In places you load MyInfo, if you load `MyDocument` at the same time (e.g.
      `select_related('document')`, then typically you'll need to you'll need to
      remember to defer loading of MyDocument.content for performance e.g.
      `defer('document__content')`

    - Remember to clean up orphaned instances of MyDocument which are left behind
      - when a new document is associated with MyInfo instance
      - when uploads are done but the MyInfo instance is not saved

      This can be done using a scheduled task that looks for MyDocument instances
      not related to a MyInfo.

    - Remember to add permissions for the file to be downloaded, in static_roles.yaml
    - Use DocumentRelatedModelAdminMixin and DocumentAdmin for admin

    """

    created_at = models.DateTimeField(default=timezone.now)
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    content = models.BinaryField()
    erased_on = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.filename}, {self.created_at}"

    class Meta:
        abstract = True

    @classmethod
    def from_upload(cls, uploaded_file):
        """
        Build a document from an UploadedFile object
        """
        content = uploaded_file.read()
        return cls(
            filename=uploaded_file.name,
            mimetype=uploaded_file.content_type,
            size=len(content),
            content=content,
        )

    def as_field_file(self):
        """
        Returns FieldFile (compatible) instance for the document.
        """
        return DocumentModelFile(self)

    @property
    def url(self):
        return self.as_field_file().url

    @property
    def download_link(self):
        return format_html("<a href={0}>{1}</a>", self.url, self.filename)

    def save(self, **kwargs):
        self.size = len(self.content)
        super().save(**kwargs)


class DocumentModelFile(File):
    """
    File subclass that handles instances of Document (subclass)
    """

    def __init__(self, document):
        self.document = document

    @property
    def size(self):
        return self.document.size

    @property
    def file(self):
        return io.BytesIO(self.document.content)

    @property
    def name(self):
        return self.document.filename

    @property
    def url(self):
        # This is used by FileInput, and by other download links via Document.url
        model = self.document.__class__
        return reverse(
            "documents-download",
            kwargs={"id": self.document.id, "app_label": model._meta.app_label, "model_name": model.__name__.lower()},
        )
