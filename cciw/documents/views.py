from django.apps import apps
from django.http import Http404, HttpRequest, HttpResponse

from .models import Document


def not_found() -> Http404:
    return Http404("Document not found, or insufficient privileges to view it.")


def download(request: HttpRequest, app_label: str, model_name: str, id: int) -> HttpResponse:
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        raise not_found()

    if not model.__base__ == Document:
        raise not_found()

    perm = f"{app_label}.view_{model_name}"
    if not request.user.has_perm(perm):
        raise not_found()

    obj = model.objects.get(id=id)

    return HttpResponse(
        content=obj.content,
        content_type=obj.mimetype,
        headers={"Content-Length": obj.size, "Content-Disposition": f'attachment; filename="{obj.filename}"'},
    )
