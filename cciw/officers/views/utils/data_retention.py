from collections.abc import Callable
from enum import StrEnum
from functools import wraps

import furl
from django.template.response import TemplateResponse


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


def show_data_retention_notice(notice_type: DataRetentionNotice, brief_title: str) -> Callable:
    """
    Decorator for downloads to show a prompt to ensure
    user knows about data retention
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            htmx = "HX-Request" in request.headers
            if "data_retention_notice_seen" in request.GET:
                return func(request, *args, **kwargs)
            else:
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
