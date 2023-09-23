from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.db.models import F, Model, Q, Value
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from paypal.standard.ipn.models import PayPalIPN

from cciw.accounts.models import User
from cciw.bookings.models import Booking, BookingAccount
from cciw.contact_us.models import Message
from cciw.data_retention.applying import (
    EraseCommand,
    build_single_model_erase_command,
    get_not_in_use_records,
    load_actual_data_retention_policy,
)
from cciw.data_retention.datatypes import Policy
from cciw.officers.models import Application

M = TypeVar("M", bound=Model)


@dataclass(kw_only=True)
class SearchResult(Generic[M]):
    pk: int
    model: type[M]
    email: str
    name: str

    # Possibly add other optional fields like phone, address?

    @property
    def model_name(self):
        return self.model._meta.label

    @property
    def result_id(self) -> str:
        return f"{self.model_name}:{self.pk}"

    @property
    def type_description(self) -> str:
        doc = self.model.__doc__
        if doc == Model.__doc__:
            doc = None
        return self.model_name + ((" - " + doc) if doc else "")

    @property
    def admin_link(self):
        url_name = admin_urlname(self.model._meta, "change")
        admin_change_url = reverse(url_name, args=[self.pk])
        return format_html('<a href="{0}" target="_new">{1}</a>', admin_change_url, self.result_id)

    def as_json(self):
        return {
            "type": "SearchResult",
            "model": self.model_name,
            "pk": self.pk,
        }


def create_filter(field: str, query_term: str):
    # TODO support multiple email addresses
    if "@" in query_term:
        return Q(**{f"{field}__iexact": query_term})
    else:
        return Q(**{f"{field}__icontains": query_term})


SEARCH_QUERIES = [
    (
        User,
        lambda query_term: User.objects.filter(create_filter("email", query_term)).values_list(
            "id",
            "email",
            Concat(F("first_name"), Value(" "), F("last_name")),
        ),
    ),
    (
        Application,
        lambda query_term: Application.objects.filter(create_filter("address_email", query_term)).values_list(
            "id",
            "address_email",
            "full_name",
        ),
    ),
    (
        BookingAccount,
        lambda query_term: BookingAccount.objects.filter(create_filter("email", query_term)).values_list(
            "id",
            "email",
            "name",
        ),
    ),
    (
        Booking,
        lambda query_term: Booking.objects.filter(create_filter("email", query_term)).values_list(
            "id",
            "email",
            Concat(F("first_name"), Value(" "), F("last_name")),
        ),
    ),
    (
        PayPalIPN,
        lambda query_term: PayPalIPN.objects.filter(create_filter("payer_email", query_term)).values_list(
            "id",
            "payer_email",
            Concat(F("first_name"), Value(" "), F("last_name")),
        ),
    ),
    (
        Message,
        lambda query_term: Message.objects.filter(create_filter("email", query_term)).values_list(
            "id",
            "email",
            "name",
        ),
    ),
    # TODO SupportingInformation (doesn't make a difference as we have
    # to keep it for 3 years, and we delete after 3 years automatically)
    # TODO mechanism for ensuring this is complete.
]

SEARCH_QUERIES_MODELS = [m for m, f in SEARCH_QUERIES]


def data_erasure_request_search(query_term: str) -> list[SearchResult]:
    query_term = query_term.strip().lower()

    results = []
    for model, query_func in SEARCH_QUERIES:
        query = query_func(query_term)
        assert model == query.model
        results.extend(
            [
                SearchResult(
                    pk=item[0],
                    model=model,
                    email=item[1],
                    name=item[2],
                )
                for item in query
            ]
        )

    return results


@dataclass(kw_only=True)
class ErasurePlanItem:
    result: SearchResult

    # The schema allows for multiple commands,
    # in reality there will always be one.
    commands: list[EraseCommand]

    @property
    def contains_empty_commands(self) -> bool:
        # commands is in practice a single item
        return any(command.is_empty for command in self.commands)

    def execute(self) -> None:
        for command in self.commands:
            command.execute()

    execute.alters_data = True  # Stop it being used in the template

    @property
    def result_id(self):
        return self.result.result_id

    @property
    def result_email(self):
        return self.result.email

    @property
    def result_type_description(self):
        return self.result.type_description

    @property
    def admin_link(self):
        return self.result.admin_link

    def as_json(self):
        return {
            "type": "ErasurePlanItem",
            "result": self.result.as_json(),
            "commands": [command.as_json() for command in self.commands],
        }


@dataclass(kw_only=True)
class ErasurePlan:
    items: list[ErasurePlanItem]

    def execute(self) -> None:
        for item in self.items:
            item.execute()

    execute.alters_data = True  # Stop it being used in the template

    def as_json(self):
        return {
            "type": "ErasurePlan",
            "items": [item.as_json() for item in self.items],
        }


def data_erasure_request_create_plan(results: list[SearchResult]) -> ErasurePlan:
    policy = load_actual_data_retention_policy()
    # We could probably pull more common work out of the loop, but this code is
    # going to be used very rarely, on very few records.
    today = timezone.now()

    return ErasurePlan(items=[build_erasure_plan_item(result, policy, today) for result in results])


def build_erasure_plan_item(result: SearchResult, policy: Policy, now: datetime) -> ErasurePlanItem:
    commands = []
    for group in policy.groups:
        if not group.rules.erasable_on_request:
            continue
        for model_detail in group.models:
            if model_detail.model != result.model:
                continue

            records = get_not_in_use_records(now, model_detail.model).filter(id=result.pk)
            command = build_single_model_erase_command(
                now=now,
                group=group,
                model_detail=model_detail,
                records=records,
            )
            commands.append(command)

    return ErasurePlanItem(result=result, commands=commands)
