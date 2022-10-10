from django import template
from django.urls import reverse

from cciw.officers.views import BreadCrumb

register = template.Library()


@register.inclusion_tag(filename="cciw/officers/breadcrumbs.html", takes_context=True)
def officers_breadcrumbs(context):
    breadcrumbs: list[BreadCrumb] = list(context.get("breadcrumbs", []))
    if "title" in context and breadcrumbs:
        breadcrumbs.append((None, context["title"]))

    return {"breadcrumbs": [(reverse(url) if url else None, caption) for url, caption in breadcrumbs]}
