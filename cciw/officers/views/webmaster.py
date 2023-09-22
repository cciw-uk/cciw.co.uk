from django import forms
from django.db import transaction
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from cciw.data_retention.erasure_requests import data_erasure_request_create_plan, data_erasure_request_search
from cciw.data_retention.models import ErasureExecutionLog

from .utils.auth import webmaster_required


class SearchForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "email", "id": "searchbar"}),
    )


@webmaster_required
def data_erasure_request_start(request: HttpRequest):
    if "query" in request.GET:
        search_form = SearchForm(request.GET)
        if search_form.is_valid():
            search_query = search_form.cleaned_data["query"]
            results = data_erasure_request_search(search_query)
        else:
            # Can't happen in practice?
            search_query = ""
            results = []
    else:
        search_form = SearchForm()
        results = None
        search_query = ""
    return TemplateResponse(
        request,
        "cciw/officers/data_erasure_request_start.html",
        {
            "title": "Data erasure request",
            "search_form": search_form,
            "search_query": search_query,
            "results": results,
        },
    )


@webmaster_required
def data_erasure_request_plan(request: HttpRequest):
    # Inputs here can come from previous page
    # (data_erasure_request_start)
    selected_result_ids: list[str] = request.GET.getlist("selected", [])
    search_query: str = request.GET.get("search_query", "")

    # To avoid needing to trust and parse selected_result_ids, we rerun the
    # query and filter the results.
    selected_results = [r for r in data_erasure_request_search(search_query) if r.result_id in selected_result_ids]
    erasure_plan = data_erasure_request_create_plan(selected_results)
    empty_items = [item for item in erasure_plan.items if item.contains_empty_commands]

    # TODO POST

    return TemplateResponse(
        request,
        "cciw/officers/data_erasure_request_plan.html",
        {
            "title": "Data erasure request - plan",
            "erasure_plan": erasure_plan,
            "empty_items": empty_items,
            # Propagate inputs:
            "search_query": search_query,
            "selected_result_ids": selected_result_ids,
        },
    )


@webmaster_required
@require_POST
def data_erasure_request_execute(request: HttpRequest):
    selected_result_ids: list[str] = request.POST.getlist("selected", [])
    search_query: str = request.POST.get("search_query", "")
    selected_results = [r for r in data_erasure_request_search(search_query) if r.result_id in selected_result_ids]
    erasure_plan = data_erasure_request_create_plan(selected_results)
    with transaction.atomic():
        plan_details = erasure_plan.as_json()
        erasure_plan.execute()
        erasure_log = ErasureExecutionLog.objects.create(
            executed_by=request.user,
            plan_details=plan_details,
        )

    return TemplateResponse(
        request,
        "cciw/officers/data_erasure_request_finished.html",
        {
            "title": "Data erasure request - executed",
            "erasure_log": erasure_log,
        },
    )
