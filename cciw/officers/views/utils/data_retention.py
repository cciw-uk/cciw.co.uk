from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import Any, Literal, Protocol, overload

import furl
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from cciw.officers.models.data_retention import DataRelation, NoDataRelation, log_data_download
from cciw.utils.views import ViewFunc


class DataRetentionNotice(StrEnum):
    OFFICERS = "officers"
    CAMPERS = "campers"


DATA_RETENTION_NOTICES_HTML = {
    DataRetentionNotice.OFFICERS: "cciw/officers/officer_data_retention_rules_inc.html",
    DataRetentionNotice.CAMPERS: "cciw/officers/camper_data_retention_rules_inc.html",
}

DATA_RETENTION_NOTICES_TXT = {
    DataRetentionNotice.OFFICERS: """
Share this data only with leaders or the designated CCiW officers
who assist leaders with tasks relating to officers, and no third parties.
All such people must be aware of and abide by these rules.

Keep downloaded data secure and well organised, stored only on devices that
unauthorised people do not have access to. You must be able to find and delete it later.

Delete officer addresses within 1 year of the end of the camp they
pertain to. They must be fully erased from your electronic devices and
online storage, including any copies you have made, such as attachments in
emails and backups.

""".strip(),
    DataRetentionNotice.CAMPERS: """
Share this data only with leaders and assistant leaders and no third parties.
All these people must be aware of and abide by these rules.

Keep downloaded data secure and well organised, stored only on devices that
unauthorised people do not have access to. You must be able to find and delete it later.

Delete camper information within 1 month of the end of the camp it relates to.
It must be fully erased from your electronic devices and online storage, including any
copies you have made, such as attachments in emails and backups.

""".strip(),
}

for val in DataRetentionNotice:
    assert val in DATA_RETENTION_NOTICES_HTML, f"Need to add {val} to DATA_RETENTION_NOTICES_HTML"
    assert val in DATA_RETENTION_NOTICES_TXT, f"Need to add {val} to DATA_RETENTION_NOTICES_TXT"


class DownloadViewFunc[**P](Protocol):
    def __call__(self, request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> SensitiveDownloadResponse: ...


class SensitiveDownloadResponse(HttpResponse):
    def __init__(self, content=b"", *args, data_relation: DataRelation, filename: str, **kwargs):
        """
        HTTP response for a sensitive download.
        """
        super().__init__(content, *args, **kwargs)
        self.data_relation = data_relation
        self.filename = filename
        self.headers["Content-Disposition"] = f"attachment; filename={filename}"


@overload
def sensitive_data_download[**P](
    *,
    skip_notice: Literal[True],
) -> Callable[[DownloadViewFunc[P]], ViewFunc[P]]: ...


@overload
def sensitive_data_download[**P](
    notice_type: DataRetentionNotice, brief_title: str, /
) -> Callable[[DownloadViewFunc[P]], ViewFunc[P]]: ...


def sensitive_data_download[**P](
    notice_type: DataRetentionNotice | None = None,
    brief_title: str | None = None,
    /,
    *,
    skip_notice: Literal[True] | None = None,
) -> Callable[[DownloadViewFunc[P]], ViewFunc[P]]:
    """
    Decorator for sensitive data downloads:

    - shows a prompt to ensure to user the knows about data retention,
      using notice_type and brief_title (unless you pass 'skip_notice=True')

    - logs the download
    """

    def decorator(func: DownloadViewFunc[P]) -> ViewFunc[P]:
        @wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            htmx = "HX-Request" in request.headers
            if "data_retention_notice_seen" in request.GET or skip_notice:
                response = func(request, *args, **kwargs)
                data_relation = response.data_relation
                if not isinstance(data_relation, NoDataRelation):
                    log_data_download(user=request.user, data_relation=data_relation, filename=response.filename)
                return response
            else:
                assert notice_type is not None
                assert brief_title is not None
                if htmx:
                    base_template = "cciw/officers/modal_dialog.html"
                else:
                    base_template = "cciw/officers/base.html"

                template = "cciw/officers/show_data_retention_notice.html"
                return TemplateResponse(
                    request,
                    template,
                    {
                        "base_template": base_template,
                        "include_file": DATA_RETENTION_NOTICES_HTML[notice_type],
                        "brief_title": brief_title,
                        "download_link": furl.furl(request.get_full_path()).add(
                            query_params={"data_retention_notice_seen": "1"}
                        ),
                    },
                )

        return wrapper

    return decorator
