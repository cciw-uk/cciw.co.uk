# We put these models here, rather than the general `cciw.data_retention` app,
# because they depend on details of officer functionality.

from dataclasses import dataclass

from django.db import models
from django.utils import timezone

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp


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
class NoDataRelation:
    """
    Sentinel that can be used when there is no sensitive data in the download
    (e.g. only stats, or nothing personal)
    """

    pass


# NOTE: changes to names of these classes will require a data migration,
# they are used in `type` field below
type LoggableDataRelation = DataRelatedToCampersYear | DataRelatedToCampersOnCamp | DataRelatedToOfficersOnCamp

type DataRelation = LoggableDataRelation | NoDataRelation


LOGGABLE_DATA_RELATION_TYPES = [cls.__name__ for cls in LoggableDataRelation.__value__.__args__]


class DataDownloadLog(models.Model):
    user = models.ForeignKey(User, related_name="data_download_logs", on_delete=models.PROTECT)
    relation_type = models.CharField(choices=[(t, t) for t in LOGGABLE_DATA_RELATION_TYPES])
    filename = models.CharField()
    created_at = models.DateTimeField(default=timezone.now)

    # Nullable fields, relating to certain DataRelation types:
    year = models.IntegerField(blank=True, null=True)
    camp = models.ForeignKey(Camp, blank=True, null=True, related_name="data_download_logs", on_delete=models.CASCADE)

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
