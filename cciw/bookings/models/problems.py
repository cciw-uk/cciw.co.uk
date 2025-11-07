from dataclasses import dataclass

from django.db import models


@dataclass(frozen=True, kw_only=True)
class Blocker:
    description: str

    @property
    def blocker(self) -> bool:
        return True

    @property
    def fixable(self) -> bool:
        return False


class FixableErrorType(models.TextChoices):
    CUSTOM_PRICE = "custom_price", "Custom price"
    SERIOUS_ILLNESS = "serious_illness", "Serious illness"
    TOO_YOUNG = "too_young", "Too young"
    TOO_OLD = "too_old", "Too old"


FET = FixableErrorType


@dataclass(frozen=True, kw_only=True)
class FixableError:
    """
    Represents booking problems that can be fixed by approval (via booking secretary)
    """

    description: str
    type: FixableErrorType

    @property
    def short_description(self) -> str:
        return self.type.label

    @property
    def blocker(self) -> bool:
        return True

    @property
    def fixable(self) -> bool:
        return True


@dataclass(frozen=True, kw_only=True)
class Warning:
    description: str

    @property
    def blocker(self) -> bool:
        return False


type BookingProblem = Blocker | FixableError | Warning
