from django.contrib import admin
from django.forms.renderers import DjangoTemplates
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict
from django.utils.safestring import SafeString


class ExplicitBooleanFieldSelect(admin.widgets.AdminRadioSelect):
    """
    A Radio select widget intended to be used with a nullable BooleanField.
    """

    def __init__(self, attrs: None = None):
        if attrs is None:
            attrs = {}
        attrs.update({"class": "radiolist inline"})
        choices = [
            ("2", "Yes"),
            ("3", "No"),
        ]
        super().__init__(attrs, choices)

    def render(
        self,
        name: str,
        value: bool | None,
        attrs: dict[str, str] | None = None,
        renderer: DjangoTemplates | None = None,
    ) -> SafeString:
        try:
            value = {True: "2", False: "3", "2": "2", "3": "3"}[value]
        except KeyError:
            value = "1"
        return super().render(name, value, attrs=attrs, renderer=renderer)

    def value_from_datadict(self, data: QueryDict, files: MultiValueDict, name: str) -> bool | None:
        value = data.get(name)
        return {
            "2": True,
            True: True,
            "True": True,
            "3": False,
            "False": False,
            False: False,
        }.get(value)
