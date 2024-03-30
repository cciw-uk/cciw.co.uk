from django import template
from django.urls import reverse

from cciw.officers.views.utils.breadcrumbs import BreadCrumb

register = template.Library()


@register.inclusion_tag(filename="cciw/officers/officers_breadcrumbs.html", takes_context=True)
def officers_breadcrumbs(context):
    breadcrumbs: list[BreadCrumb] = list(context.get("breadcrumbs", []))
    if "title" in context and breadcrumbs:
        breadcrumbs.append((None, context["title"]))

    return {"breadcrumbs": [(reverse(url) if url else None, caption) for url, caption in breadcrumbs]}


@register.filter
def pretty_join(values: list[str]):
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return ", ".join(values[0:-1]) + " and " + values[-1]
