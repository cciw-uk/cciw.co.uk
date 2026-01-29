from django.conf import settings
from django.http import HttpRequest
from django.template.response import TemplateResponse

from cciw.utils.literate_yaml import literate_yaml_to_rst
from cciw.utils.rst import remove_rst_title, rst_to_html


def data_retention_policy(request: HttpRequest) -> TemplateResponse:
    policy = open(settings.DATA_RETENTION_CONFIG_FILE).read()
    return TemplateResponse(
        request,
        "cciw/data_retention_policy.html",
        {
            "title": "Data retention policy",
            "data_retention_policy": rst_to_html(
                remove_rst_title(literate_yaml_to_rst(policy)), initial_header_level=2
            ),
        },
    )
