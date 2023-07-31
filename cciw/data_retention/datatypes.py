from __future__ import annotations

import dataclasses
from datetime import timedelta
from typing import TYPE_CHECKING

import pydantic.dataclasses
from django.db import models
from django.db.models.fields import Field


class DataclassConfig:
    arbitrary_types_allowed = True


dataclass = pydantic.dataclasses.dataclass(config=DataclassConfig)

if TYPE_CHECKING:
    # Help some type checkers/IDE tools to understand pydantic
    from dataclasses import dataclass


# --- Policy and sub-components ---
#
# The YAML file is parsed into these objects.


@dataclass
class Policy:
    """
    The entire data retention policy, which we have only one of in production.
    """

    source: str
    groups: list[Group]


@dataclass
class Group:
    name: str
    rules: Rules
    models: list[ModelDetail]


@dataclass
class Rules:
    keep: Keep
    erasable_on_request: bool


@dataclass
class ModelDetail:
    model: type[models.Model]
    fields: list[Field]
    custom_erasure_methods: dict[Field, ErasureMethod] = dataclasses.field(default_factory=dict)
    delete_row: bool = False


class ForeverType:
    pass


Forever = ForeverType()

Keep = timedelta | ForeverType


class ErasureMethod:
    def allowed_for_field(self, field: Field) -> bool:
        raise NotImplementedError(f"{self.__class__} needs to implement allowed_for_field")

    def build_update_dict(self, field) -> dict:
        """
        Returns a dict which can be passed as keyword arguments
        to a QuerySet.update() call.
        """
        raise NotImplementedError(f"{self.__class__} needs to implement build_update_dict")


Policy.__pydantic_model__.update_forward_refs()
Group.__pydantic_model__.update_forward_refs()
Rules.__pydantic_model__.update_forward_refs()
ModelDetail.__pydantic_model__.update_forward_refs()
