import contextlib
import json
import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from paypal.standard.forms import PayPalPaymentsForm

from cciw.bookings.email import send_verify_email
from cciw.bookings.forms import AccountDetailsForm, AddPlaceForm, EmailForm, UsePreviousData
from cciw.bookings.middleware import unset_booking_account_cookie
from cciw.bookings.models import (
    BOOKING_ACCOUNT_ADDRESS_TO_CAMPER_ADDRESS_FIELDS,
    BOOKING_ACCOUNT_ADDRESS_TO_CONTACT_ADDRESS_FIELDS,
    BOOKING_PLACE_CAMPER_ADDRESS_DETAILS,
    BOOKING_PLACE_CAMPER_DETAILS,
    BOOKING_PLACE_CONTACT_ADDRESS_DETAILS,
    BOOKING_PLACE_GP_DETAILS,
    AgreementFetcher,
    Booking,
    BookingAccount,
    CustomAgreement,
    Price,
    PriceType,
    any_bookings_possible,
    build_paypal_custom_field,
    early_bird_is_available,
    get_booking_open_data,
    get_booking_open_data_thisyear,
    get_early_bird_cutoff_date,
)
from cciw.bookings.models.baskets import add_basket_to_queue
from cciw.bookings.models.prices import PriceInfo
from cciw.bookings.models.problems import ApprovalNeeded
from cciw.cciwmain import common
from cciw.cciwmain.common import get_current_domain, get_thisyear, htmx_form_validate
from cciw.officers.views.utils.htmx import add_hx_trigger_header
from cciw.utils.views import for_htmx, for_htmx2, htmx_redirect, make_get_request

from .decorators import (
    account_details_required,
    booking_account_optional,
    booking_account_required,
    redirect_if_agreement_fix_required,
)

# utilities


class BookingStage:
    ACCOUNT = "account"
    OVERVIEW = "overview"
    PLACE = "place"
    LIST = "list"
    PAY = "pay"


# Views


@booking_account_optional
def index(request):
    year = common.get_thisyear()
    context: dict = {
        "title": "Booking",
    }
    booking_open = get_booking_open_data(year)
    price_info = PriceInfo.get_for_year(year=year)
    prices_set = price_info is not None

    if price_info:
        prices_to_show = price_info
    else:
        # Show last year's prices
        prices_to_show = PriceInfo.get_for_year(year=year - 1)

    context.update(
        {
            "prices_to_show": prices_to_show,
            "prices_set": prices_set,
            "booking_open_data": booking_open,
            "any_bookings_possible": any_bookings_possible(common.get_thisyear()),
        }
    )
    return TemplateResponse(request, "cciw/bookings/index.html", context)


def next_step(account):
    """
    Returns a redirect to the next obvious step for this account.
    """
    if account.has_account_details():
        bookings = account.bookings.for_year(common.get_thisyear())
        if (bookings.in_basket() | bookings.on_shelf() | bookings.booked()).exists():
            return HttpResponseRedirect(reverse("cciw-bookings-account_overview"))
        else:
            return HttpResponseRedirect(reverse("cciw-bookings-add_place"))
    else:
        return HttpResponseRedirect(reverse("cciw-bookings-account_details"))


@booking_account_optional
def start(request):
    form_class = EmailForm
    account = request.booking_account
    if account is not None:
        return next_step(account)
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            send_verify_email(request, email)
            return HttpResponseRedirect(reverse("cciw-bookings-email_sent"))
    else:
        form = form_class()

    return TemplateResponse(
        request,
        "cciw/bookings/start.html",
        {
            "title": "Booking - log in",
            "booking_open_data": get_booking_open_data_thisyear(),
            "form": form,
            "any_bookings_possible": any_bookings_possible(common.get_thisyear()),
        },
    )


@booking_account_optional
def email_sent(request):
    return TemplateResponse(
        request,
        "cciw/bookings/email_sent.html",
        {
            "title": "Booking - log in",
        },
    )


@booking_account_optional
def link_expired_email_sent(request):
    return TemplateResponse(
        request,
        "cciw/bookings/email_sent.html",
        {
            "title": "Booking - log in",
            "link_expired": True,
        },
    )


@booking_account_required
def verify_and_continue(request):
    # Verification and login already done by the middleware,
    # checking already done by booking_account_required.
    account = request.booking_account

    now = timezone.now()
    last_login_at = account.last_login_at

    if account.first_login_at is None:
        account.first_login_at = now
    account.last_login_at = now
    account.save()

    if last_login_at is not None and ((now - last_login_at) > timedelta(30 * 6)):  # six months
        messages.info(request, "Welcome back! Please check and update your account details")
        return HttpResponseRedirect(reverse("cciw-bookings-account_details"))
    else:
        return next_step(account)


@booking_account_optional
def verify_email_failed(request):
    return TemplateResponse(
        request,
        "cciw/bookings/email_verification_failed.html",
        {
            "title": "Booking - account email verification failed",
        },
    )


@booking_account_optional
def not_logged_in(request):
    return TemplateResponse(
        request,
        "cciw/bookings/not_logged_in.html",
        {
            "title": "Booking - not logged in",
        },
    )


@booking_account_required
@htmx_form_validate(form_class=AccountDetailsForm)
def account_details(request):
    form_class = AccountDetailsForm

    if request.method == "POST":
        form = form_class(request.POST, instance=request.booking_account)
        if form.is_valid():
            form.save()
            messages.info(request, "Account details updated, thank you.")
            return next_step(request.booking_account)
    else:
        form = form_class(instance=request.booking_account)
    return TemplateResponse(
        request,
        "cciw/bookings/account_details.html",
        {
            "title": "Booking - account details",
            "stage": BookingStage.ACCOUNT,
            "form": form,
        },
    )


@account_details_required
def add_or_edit_place(
    request,
    booking_id: int | None = None,
    *,
    context: dict | None = None,
    form_input_data: dict | None = None,
    extra_response_headers: dict | None = None,
):
    context = context or {}
    form_class = AddPlaceForm
    year = common.get_thisyear()
    now = timezone.now()
    booking_account = request.booking_account
    booking_open = get_booking_open_data_thisyear()

    if request.method == "POST" and not booking_open.is_open_for_entry:
        # Redirect to same view, but GET
        return HttpResponseRedirect(request.get_full_path())

    if booking_id is not None:
        # Edit
        try:
            booking: Booking = booking_account.bookings.get(id=booking_id)
            state_was_booked = booking.is_booked
        except (ValueError, Booking.DoesNotExist):
            raise Http404
        if request.method == "POST" and not booking.is_user_editable():
            # Redirect to same view, but GET
            return HttpResponseRedirect(request.get_full_path())
        context.update(title="Booking - edit camper details", edit_mode=True)
    else:
        # Add
        booking = None
        state_was_booked = False
        context.update(title="Booking - add new camper details")

    custom_agreements = CustomAgreement.objects.for_year(year)
    if request.method == "POST":
        form = form_class(request.POST, instance=booking)
        if form.is_valid():
            booking = form.instance
            custom_agreements_checked = [
                agreement for agreement in custom_agreements if f"custom_agreement_{agreement.id}" in request.POST
            ]
            booking.save_for_account(
                account=booking_account,
                state_was_booked=state_was_booked,
                custom_agreements=custom_agreements_checked,
            )
            messages.info(request, f'Details for "{booking.name}" were saved successfully')
            return HttpResponseRedirect(reverse("cciw-bookings-basket_list_bookings"))
    else:
        form = form_class(data=form_input_data, instance=booking)

    context.update(
        {
            "booking_open_data": get_booking_open_data_thisyear(),
            "stage": BookingStage.PLACE,
            "form": form,
            "early_bird_available": early_bird_is_available(year=year, booked_at=now),
            "early_bird_date": get_early_bird_cutoff_date(year),
            "price_early_bird_discount": lambda: Price.objects.get(
                year=year, price_type=PriceType.EARLY_BIRD_DISCOUNT
            ).price,
            "read_only": booking is not None and not booking.is_user_editable(),
            "custom_agreements": custom_agreements,
            "booking": booking,
            "reuse_data_url": _reuse_data_url(booking.id if booking else None),
            "use_previous_data_modal_url": _use_previous_data_modal_url(booking.id if booking else None),
        }
    )
    return TemplateResponse(request, "cciw/bookings/add_place.html", context, headers=extra_response_headers)


@booking_account_required
@redirect_if_agreement_fix_required  # Don't allow to add new until booked places fixed
def add_place(request):
    return add_or_edit_place(request)


@booking_account_required
def edit_place(request, booking_id: int):
    return add_or_edit_place(request, booking_id=booking_id)


@booking_account_required
@for_htmx(use_block_from_params=True)
@require_GET
def add_place_reuse_data(request: HttpRequest, booking_id: int | None = None):
    """
    Adds in additional data to the form on the page, depending on the buttons used.
    """
    # Triggered from the add_place.html page, and from the use_previous_data_modal.html page
    booking_account = request.booking_account
    form_data = request.GET.copy()
    extra_response_headers = {}

    if "copy_account_address_to_camper" in request.GET:
        for field_from, field_to in BOOKING_ACCOUNT_ADDRESS_TO_CAMPER_ADDRESS_FIELDS.items():
            form_data[field_to] = getattr(booking_account, field_from)

    if "copy_account_address_to_contact_details" in request.GET:
        for field_from, field_to in BOOKING_ACCOUNT_ADDRESS_TO_CONTACT_ADDRESS_FIELDS.items():
            form_data[field_to] = getattr(booking_account, field_from)

    if from_booking_id := request.GET.get("copy_from_booking", None):
        previous_booking = booking_account.bookings.all().non_erased().get(id=from_booking_id)
        for key, fields in [
            ("copy_camper_details", BOOKING_PLACE_CAMPER_DETAILS),
            ("copy_address_details", BOOKING_PLACE_CAMPER_ADDRESS_DETAILS),
            ("copy_contact_address_details", BOOKING_PLACE_CONTACT_ADDRESS_DETAILS),
            ("copy_gp_details", BOOKING_PLACE_GP_DETAILS),
        ]:
            if key in request.GET:
                for f in fields:
                    form_data[f] = getattr(previous_booking, f)

        extra_response_headers = {"Hx-Trigger": json.dumps({"jsCloseModal": True})}

    return add_or_edit_place(
        request, form_input_data=form_data, booking_id=booking_id, extra_response_headers=extra_response_headers
    )


@booking_account_required
def use_previous_data_modal(request: HttpRequest, booking_id: int | None = None):
    booking_account = request.booking_account
    previous_bookings = booking_account.bookings.all().non_erased()
    if booking_id is not None:
        previous_bookings = previous_bookings.exclude(id=booking_id)
    form = UsePreviousData(previous_bookings=previous_bookings)
    return TemplateResponse(
        request,
        "cciw/bookings/use_previous_data_modal.html",
        {
            "form": form,
            "previous_bookings": previous_bookings,
            "reuse_data_url": _reuse_data_url(booking_id),
        },
    )


def _reuse_data_url(booking_id: int | None):
    if booking_id:
        return reverse("cciw-bookings-add_place_reuse_data", kwargs=dict(booking_id=booking_id))
    else:
        return reverse("cciw-bookings-add_place_reuse_data")


def _use_previous_data_modal_url(booking_id: int | None):
    if booking_id:
        return reverse("cciw-bookings-use_previous_data_modal", kwargs=dict(booking_id=booking_id))
    else:
        return reverse("cciw-bookings-use_previous_data_modal")


def make_state_token(bookings):
    # Hash some key data about booking, without which the booking isn't valid.
    # This is a protection mechanism for the user's benefit, to ensure they
    # don't accidentally book something significantly different from what they
    # expect (due to, for example, changing a booking in a different tab). For
    # this reason we don't need all info.
    data = "|".join(
        [
            ":".join(map(str, [b.id, b.camp.id, b.amount_due, b.name, b.price_type, b.state]))
            for b in sorted(bookings, key=lambda b: b.id)
        ]
    )
    return salted_hmac("cciw.bookings.state_token", data.encode("utf-8")).hexdigest()


@booking_account_required
@redirect_if_agreement_fix_required
@for_htmx(use_block_from_params=True)
def basket_list_bookings(request):
    """
    List bookings ready to book
    """
    return _basket_list_bookings(request)


def _basket_list_bookings(request: HttpRequest):
    year = common.get_thisyear()
    booking_open_data = get_booking_open_data(year)
    now = timezone.now()
    bookings = (
        request.booking_account.bookings.for_year(year)
        .order_by("id")
        .not_in_queue()
        .with_prefetch_camp_info()
        .with_approvals()
    )
    # NB - use lists here, not querysets, so that both state_token and book_now
    # functionality apply against same set of bookings.
    basket_bookings: list[Booking] = list(bookings.in_basket())
    shelf_bookings: list[Booking] = list(bookings.on_shelf())

    if request.method == "POST":
        if "add_another" in request.POST:
            return HttpResponseRedirect(reverse("cciw-bookings-add_place"))

        places = basket_bookings + shelf_bookings
        handled = _handle_list_booking_actions(request, places)
        if handled is True:
            return _basket_list_bookings(make_get_request(request))
        elif isinstance(handled, HttpResponse):
            return handled

        if "book_now" in request.POST:
            state_token = request.POST.get("state_token", "")
            if make_state_token(basket_bookings) != state_token:
                messages.error(
                    request,
                    "Places were not booked due to modifications made "
                    "to the details. Please check the details and try again.",
                )
            else:
                if add_basket_to_queue(basket_bookings, by_user=request.booking_account):
                    messages.info(request, "Places added to queue!")
                    return HttpResponseRedirect(reverse("cciw-bookings-added_to_queue"))
                else:
                    messages.error(request, "These places cannot be booked for the reasons given below.")
            # Start over, because things may have changed.
            return HttpResponseRedirect(request.path)

    # Now apply business rules and other custom processing
    total = Decimal("0.00")
    all_bookable = True
    all_unbookable = True
    agreement_fetcher = AgreementFetcher()
    for booking_list in basket_bookings, shelf_bookings:
        b: Booking
        for b in booking_list:
            # decorate object with some attributes to make it easier in template
            problems = b.get_booking_problems(agreement_fetcher=agreement_fetcher)
            any_blocker = any(p.blocker for p in problems)
            b.bookable = not any_blocker
            b.problems = problems

            # For basket bookings only:
            if not b.shelved:
                if b.bookable:
                    all_unbookable = False
                else:
                    all_bookable = False

                if b.amount_due_confirmed is None or total is None:
                    total = None
                else:
                    total = total + b.amount_due_confirmed

    discounts = defaultdict(lambda: Decimal("0.00"))
    for b in basket_bookings:
        for name, amount in b.get_available_discounts(now):
            discounts[name] += amount

    if total is not None:
        total_discount = sum(discounts.values())
        grand_total = total - total_discount
    else:
        grand_total = None

    shelf_bookings_problems_pending_approval = any(
        isinstance(problem, ApprovalNeeded) and problem.is_pending
        for booking in shelf_bookings
        for problem in booking.problems
    )

    # There is no point in "Save for later" if they can't
    # press "Apply now":
    show_save_for_later_button = booking_open_data.is_open_for_booking

    return TemplateResponse(
        request,
        "cciw/bookings/list_bookings.html",
        {
            "title": "Booking - checkout",
            "stage": BookingStage.LIST,
            "basket_bookings": basket_bookings,
            "shelf_bookings": shelf_bookings,
            "shelf_bookings_problems_pending_approval": shelf_bookings_problems_pending_approval,
            "all_bookable": all_bookable,
            "all_unbookable": all_unbookable,
            "state_token": make_state_token(basket_bookings),
            "total": total,
            "grand_total": grand_total,
            "discounts_available": discounts.items(),
            "booking_open_data": booking_open_data,
            "show_save_for_later_button": show_save_for_later_button,
        },
    )


def _handle_list_booking_actions(request: HttpRequest, places: list[Booking]) -> bool | HttpResponse:
    if "booking_id" not in request.POST:
        return False

    try:
        place: Booking = [p for p in places if p.id == int(request.POST["booking_id"])][0]
    except (ValueError, IndexError):
        return False

    if "shelve" in request.POST:
        place.move_to_shelf()
        return True
    elif "unshelve" in request.POST:
        place.move_to_basket()
        return True
    elif "delete" in request.POST:
        place.delete()
        return True
    elif "edit" in request.POST:
        return htmx_redirect(reverse("cciw-bookings-edit_place", kwargs={"booking_id": str(place.id)}))

    return False


@booking_account_required
def added_to_queue(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "cciw/bookings/added_to_queue.html",
        {
            "title": "Booking - added to queue",
            "booking_open_data": get_booking_open_data(get_thisyear()),
        },
    )


class CustomAmountPayPalForm(PayPalPaymentsForm):
    amount = forms.IntegerField(widget=forms.widgets.NumberInput)


def mk_paypal_form(
    account, balance, protocol, domain, min_amount=None, max_amount=None, item_name="Camp place booking"
):
    paypal_dict = {
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": str(balance),
        "item_name": item_name,
        # We don't need this info, but invoice numbermust be unique
        "invoice": f"{account.id}-{balance}-{timezone.now()}",
        "notify_url": f"{protocol}://{domain}{reverse('paypal-ipn')}",
        "return": f"{protocol}://{domain}{reverse('cciw-bookings-pay_done')}",
        "cancel_return": f"{protocol}://{domain}{reverse('cciw-bookings-pay_cancelled')}",
        "custom": build_paypal_custom_field(account),
        "currency_code": "GBP",
        "no_note": "1",
        "no_shipping": "1",
    }
    if min_amount is not None or max_amount is not None:
        cls = CustomAmountPayPalForm
    else:
        cls = PayPalPaymentsForm

    form = cls(initial=paypal_dict)
    if min_amount is not None:
        form.fields["amount"].widget.attrs.update({"min": str(min_amount), "value": str(min_amount)})

    if max_amount is not None:
        form.fields["amount"].widget.attrs["max"] = str(max_amount)

    return form


@booking_account_required
@redirect_if_agreement_fix_required
def pay(request, *, installment: bool = False):
    acc: BookingAccount = request.booking_account
    balance_due_now = acc.get_balance_due_now()
    balance_full = acc.get_balance_full()

    domain = get_current_domain()
    protocol = "https" if request.is_secure() else "http"

    custom_min_amount = 0 if installment else max(balance_due_now, 0)
    custom_max_amount = balance_full

    return TemplateResponse(
        request,
        "cciw/bookings/pay.html",
        {
            "stage": BookingStage.PAY,
            "title": "Booking - payment",
            "balance_due_now": balance_due_now,
            "balance_full": balance_full,
            "account_id": acc.id,
            "pending_payment_total": acc.get_pending_payment_total(),
            "paypal_form": mk_paypal_form(acc, balance_due_now, protocol, domain),
            "paypal_form_full": mk_paypal_form(acc, balance_full, protocol, domain),
            "paypal_form_custom": mk_paypal_form(
                acc,
                max(0, balance_due_now),
                protocol,
                domain,
                min_amount=custom_min_amount,
                max_amount=custom_max_amount,
            ),
            "paypal_form_other_person": mk_paypal_form(
                acc,
                0,
                protocol,
                domain,
                min_amount=0,
                item_name="Payment for someone else",
            ),
            "installment": installment,
        },
    )


@csrf_exempt  # PayPal will post to this
@booking_account_optional
def pay_done(request):
    return TemplateResponse(
        request,
        "cciw/bookings/pay_done.html",
        {
            "title": "Booking - payment complete",
            "stage": BookingStage.PAY,
        },
    )


@csrf_exempt  # PayPal will post to this
@booking_account_optional
def pay_cancelled(request):
    return TemplateResponse(
        request,
        "cciw/bookings/pay_cancelled.html",
        {
            "title": "Booking - payment cancelled",
            "stage": BookingStage.PAY,
        },
    )


@booking_account_required
@for_htmx2(use_partial_from_params=True)
def account_overview(request):
    if "logout" in request.POST:
        response = HttpResponseRedirect(reverse("cciw-bookings-index"))
        unset_booking_account_cookie(response)
        return response

    account: BookingAccount = request.booking_account
    year = common.get_thisyear()
    bookings = account.bookings.for_year(year)
    agreement_fetcher = AgreementFetcher()

    if request.method == "POST":
        if response := _handle_overview_booking_actions(request, bookings):
            return response

    booked_places = bookings.booked().with_prefetch_camp_info().with_prefetch_missing_agreements(agreement_fetcher)
    waiting_places = (
        bookings.waiting_in_queue().with_prefetch_camp_info().with_prefetch_missing_agreements(agreement_fetcher)
    )
    not_in_queue_places = bookings.not_in_queue()
    basket_or_shelf_places = (
        not_in_queue_places.in_basket() | not_in_queue_places.on_shelf()
    ).with_prefetch_camp_info()
    return TemplateResponse(
        request,
        "cciw/bookings/account_overview.html",
        {
            "title": "Booking - account overview",
            "stage": BookingStage.OVERVIEW,
            "booked_places": booked_places,
            "waiting_places": waiting_places,
            "cancelled_places": bookings.cancelled().with_prefetch_camp_info(),
            "basket_or_shelf_places": basket_or_shelf_places,
            "balance_due_now": (balance_due_now := account.get_balance_due_now()),
            "payment_required": balance_due_now > 0,
            "balance_full": account.get_balance_full(),
            "pending_payment_total": account.get_pending_payment_total(),
        },
    )


def _handle_overview_booking_actions(request, bookings):
    fixable_bookings = list(bookings.agreement_fix_required())

    def edit(booking):
        return HttpResponseRedirect(reverse("cciw-bookings-edit_place", kwargs={"booking_id": str(booking.id)}))

    def cancel(booking):
        booking.cancel_and_move_to_shelf()
        messages.info(request, f'Place for "{booking.name}" cancelled and put in "Saved for later".')
        return HttpResponseRedirect(reverse("cciw-bookings-account_overview"))

    for key in request.POST.keys():
        for regex, action in [
            (r"edit_(\d+)", edit),
            (r"cancel_(\d+)", cancel),
        ]:
            if match := re.match(regex, key):
                booking = None
                booking_id = int(match.groups()[0])
                with contextlib.suppress(IndexError):
                    booking = [b for b in fixable_bookings if b.id == booking_id][0]
                if booking:
                    return action(booking)


@booking_account_required
def manage_queue_booking_modal(request: HttpRequest, booking_id: int) -> HttpResponse:
    account: BookingAccount = request.booking_account
    booking: Booking = get_object_or_404(account.bookings.filter(id=booking_id))
    booking_open_data = get_booking_open_data(booking.camp.year)

    if request.method == "POST" and "withdraw" in request.POST:
        booking.withdraw_from_queue(by_user=account)
        booking.move_to_shelf()
        return add_hx_trigger_header(
            HttpResponse(b""),
            {
                "refreshPlacesInfo": True,
                "jsCloseModal": True,
            },
        )

    return TemplateResponse(
        request,
        "cciw/bookings/manage_queue_booking_modal.html",
        {
            "booking": booking,
            "booking_open_data": booking_open_data,
        },
    )
