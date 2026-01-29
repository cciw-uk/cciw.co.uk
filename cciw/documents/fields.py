from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models

from .models import Document, DocumentModelFile

# Database field:


class DocumentField(models.OneToOneField):
    """
    A field that is a OneToOne at the database level, but works
    as a file upload field in terms of interface. The related
    model is the `Document` subclass where we will store the file.
    """

    def formfield(self, **kwargs) -> "DocumentFormField":
        document_model = self.related_model
        max_length = document_model._meta.get_field("filename").max_length
        return super().formfield(
            **{
                "form_class": DocumentFormField,
                "max_length": max_length,
                "document_model": document_model,
                **kwargs,
            }
        )

    def value_from_object(self, obj: models.Model) -> DocumentModelFile:
        # This is called by model_to_dict, which is used by
        # ModelForm to create the initial data, which will be
        # used by DocumentFormField. So we have to return something
        # that can be rendered by that form field and widget
        # We have to return something that will make
        if getattr(obj, self.attname) is None:
            return None
        document_instance: Document = getattr(obj, self.name)
        return document_instance.as_field_file()


# Form field:


class DocumentFormField(forms.FileField):
    """
    Form field that allows uploads to a specific Document subclass.
    Used by DocumentField.formfield
    """

    def __init__(self, *, document_model, **kwargs):
        self.document_model = document_model
        # Some kwargs don't apply to FileField, but Field.formfield and
        # RelatedField.formfield like to pass them. (These are effectively
        # replaced by our `document_model` arg)
        kwargs.pop("limit_choices_to")
        kwargs.pop("queryset")
        kwargs.pop("to_field_name")
        kwargs.pop("blank")
        super().__init__(**kwargs)

    def to_python(self, data: InMemoryUploadedFile | None) -> Document | None:
        # Need to convert incoming file upload into a Python value
        # i.e. convert to Document (subclass) instance in our case
        data = super().to_python(data)
        if data is None:
            return data
        document_instance = self.document_model.from_upload(data)
        document_instance.save()
        return document_instance

    def clean(
        self, data: InMemoryUploadedFile | bool | None, initial: DocumentModelFile | None = None
    ) -> Document | None:
        cleaned = super().clean(data, initial=initial)
        if isinstance(cleaned, DocumentModelFile):
            # We get this if we have an initial value, from the saved data. Need
            # to convert back to something acceptable to save to the model field
            cleaned = cleaned.document
        elif cleaned is False:
            return None
        return cleaned
