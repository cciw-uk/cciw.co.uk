# We put these models here, rather than the general `cciw.data_retention` app,
# because they depend on details of officer functionality.
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from django.db import models
from django.utils import timezone

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp


class DataRetentionRule(StrEnum):
    OFFICERS = "officers"
    CAMPERS = "campers"


DATA_RETENTION_PERIODS = {
    # See also messages in DATA_RETENTION_NOTICES_* etc. if changing these, HTML and TXT
    DataRetentionRule.OFFICERS: timedelta(days=365),
    DataRetentionRule.CAMPERS: timedelta(days=31),
}

for val in DataRetentionRule:
    assert val in DATA_RETENTION_PERIODS, f"Need to add {val} to DATA_RETENTION_PERIODS"


@dataclass(frozen=True)
class DataRelatedToCampersYear:
    year: int


@dataclass(frozen=True)
class DataRelatedToCampersOnCamp:
    camp: Camp


@dataclass(frozen=True)
class DataRelatedToOfficersOnCamp:
    camp: Camp


@dataclass(frozen=True)
class NoSensitiveData:
    """
    Sentinel that can be used when there is no sensitive data in the download
    (e.g. only stats, or nothing personal)
    """

    pass


# NOTE: changes to names of these classes will require a data migration,
# they are used in `type` field below
type LoggableDataRelation = DataRelatedToCampersYear | DataRelatedToCampersOnCamp | DataRelatedToOfficersOnCamp

type DataRelation = LoggableDataRelation | NoSensitiveData


LOGGABLE_DATA_RELATION_TYPES = [cls.__name__ for cls in LoggableDataRelation.__value__.__args__]


class DataDownloadLogQuerySet(models.QuerySet):
    def for_user(self, user: User) -> DataDownloadLogQuerySet:
        return self.filter(user=user)

    def for_relation(self, data_relation: LoggableDataRelation):
        return self.filter(**data_relation_to_specific_log_fields(data_relation))


class DataDownloadLog(models.Model):
    user = models.ForeignKey(User, related_name="data_download_logs", on_delete=models.PROTECT)
    relation_type = models.CharField(choices=[(t, t) for t in LOGGABLE_DATA_RELATION_TYPES])
    filename = models.CharField()
    created_at = models.DateTimeField(default=timezone.now)

    # Nullable fields, relating to certain DataRelation types:
    year = models.IntegerField(blank=True, null=True)
    camp = models.ForeignKey(Camp, blank=True, null=True, related_name="data_download_logs", on_delete=models.CASCADE)

    objects = DataDownloadLogQuerySet.as_manager()

    def __str__(self) -> str:
        return f"Data download of {self.filename} by {self.user.username} at {self.created_at}"


def log_data_download(*, user: User, data_relation: LoggableDataRelation, filename: str) -> DataDownloadLog:
    relation_type = data_relation.__class__.__name__
    specific_fields = data_relation_to_specific_log_fields(data_relation)
    return DataDownloadLog.objects.create(user=user, relation_type=relation_type, filename=filename, **specific_fields)


def data_relation_to_specific_log_fields(data_relation: LoggableDataRelation) -> dict:
    match data_relation:
        case DataRelatedToCampersYear(year=year):
            return {"year": year}
        case DataRelatedToCampersOnCamp(camp=camp):
            return {"camp": camp}
        case DataRelatedToOfficersOnCamp(camp=camp):
            return {"camp": camp}
