import contextlib
import os
import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm

from cciw.bookings.email import send_verify_email
from cciw.bookings.forms import AccountDetailsForm, AddPlaceForm, EmailForm
from cciw.bookings.middleware import unset_booking_account_cookie
from cciw.bookings.models import (
    AgreementFetcher,
    Booking,
    BookingAccount,
    BookingState,
    CustomAgreement,
    Price,
    PriceChecker,
    PriceType,
    any_bookings_possible,
    book_basket_now,
    build_paypal_custom_field,
    early_bird_is_available,
    get_early_bird_cutoff_date,
    is_booking_open,
    is_booking_open_thisyear,
)
from cciw.cciwmain import common
from cciw.cciwmain.common import ajax_form_validate, get_current_domain
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp

from .decorators import (
    account_details_required,
    booking_account_optional,
    booking_account_required,
    redirect_if_agreement_fix_required,
)
from .utils import account_to_dict, booking_to_dict

# utilities


class BookingStage:
    LOGIN = "login"
    ACCOUNT = "account"
    OVERVIEW = "overview"
    PLACE = "place"
    LIST = "list"
    PAY = "pay"


# Views


@booking_account_optional
def index(request):
    year = common.get_thisyear()
    bookingform_relpath = f"{settings.BOOKINGFORMDIR}/booking_form_{year}.pdf"
    context = {
        "title": "Booking",
    }
    if os.path.isfile(f"{settings.MEDIA_ROOT}/{bookingform_relpath}"):
        context["bookingform"] = bookingform_relpath
    booking_open = is_booking_open(year)
    if booking_open:
        prices = Price.objects.for_year(year)
        now = timezone.now()
        early_bird_available = early_bird_is_available(year, now)
        context["early_bird_available"] = early_bird_available
        context["early_bird_date"] = get_early_bird_cutoff_date(year)
    else:
        # Show last year's prices
        prices = Price.objects.for_year(year - 1)
        early_bird_available = False

    prices = list(prices.required_for_booking())

    def getp(v):
        try:
            return [p for p in prices if p.price_type == v][0].price
        except IndexError:
            return None

    early_bird_discount = getp(PriceType.EARLY_BIRD_DISCOUNT)
    price_list = [
        ("Full price", getp(PriceType.FULL)),
        ("2nd camper from the same family", getp(PriceType.SECOND_CHILD)),
        ("Subsequent children from the same family", getp(PriceType.THIRD_CHILD)),
    ]
    if any(p is None for caption, p in price_list):
        price_list = []
    # Add discounts:
    price_list = [
        (caption, p, p - early_bird_discount if early_bird_discount is not None else 0) for caption, p in price_list
    ]

    context.update(
        {
            "price_list": price_list,
            "price_deposit": getp(PriceType.DEPOSIT),
            "price_early_bird_discount": early_bird_discount,
            "booking_open": booking_open,
            "any_bookings_possible": any_bookings_possible(common.get_thisyear()),
            "full_payment_due_time": settings.BOOKING_FULL_PAYMENT_DUE_DISPLAY,
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
            "stage": BookingStage.LOGIN,
            "title": "Booking - log in",
            "booking_open": is_booking_open_thisyear(),
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
            "stage": BookingStage.LOGIN,
            "title": "Booking - log in",
        },
    )


@booking_account_optional
def link_expired_email_sent(request):
    return TemplateResponse(
        request,
        "cciw/bookings/email_sent.html",
        {
            "stage": BookingStage.LOGIN,
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
    last_login = account.last_login

    if account.first_login is None:
        account.first_login = now
    account.last_login = now
    account.save()

    if last_login is not None and ((now - last_login) > timedelta(30 * 6)):  # six months
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
            "stage": BookingStage.LOGIN,
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
@ajax_form_validate(AccountDetailsForm)
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


@booking_account_required
@account_details_required
@ajax_form_validate(AddPlaceForm)
def add_or_edit_place(request, context, booking_id=None):
    form_class = AddPlaceForm
    year = common.get_thisyear()
    now = timezone.now()

    if request.method == "POST" and not is_booking_open_thisyear():
        # Redirect to same view, but GET
        return HttpResponseRedirect(request.get_full_path())

    if booking_id is not None:
        # Edit
        try:
            booking = request.booking_account.bookings.get(id=booking_id)
            state_was_booked = booking.is_booked
        except (ValueError, Booking.DoesNotExist):
            raise Http404
        if request.method == "POST" and not booking.is_user_editable():
            # Redirect to same view, but GET
            return HttpResponseRedirect(request.get_full_path())
    else:
        # Add
        booking = None
        state_was_booked = False

    custom_agreements = CustomAgreement.objects.for_year(year)
    if request.method == "POST":
        form = form_class(request.POST, instance=booking)
        if form.is_valid():
            booking: Booking = form.instance
            custom_agreements_checked = [
                agreement for agreement in custom_agreements if f"custom_agreement_{agreement.id}" in request.POST
            ]
            booking.save_for_account(
                account=request.booking_account,
                state_was_booked=state_was_booked,
                custom_agreements=custom_agreements_checked,
            )
            messages.info(request, f'Details for "{booking.name}" were saved successfully')
            return HttpResponseRedirect(reverse("cciw-bookings-list_bookings"))
    else:
        form = form_class(instance=booking)

    context.update(
        {
            "booking_open": is_booking_open_thisyear(),
            "stage": BookingStage.PLACE,
            "form": form,
            "early_bird_available": early_bird_is_available(year, now),
            "early_bird_date": get_early_bird_cutoff_date(year),
            "price_early_bird_discount": lambda: Price.objects.get(
                year=year, price_type=PriceType.EARLY_BIRD_DISCOUNT
            ).price,
            "read_only": booking is not None and not booking.is_user_editable(),
            "custom_agreements": custom_agreements,
        }
    )
    return TemplateResponse(request, "cciw/bookings/add_place.html", context)


@booking_account_required
@redirect_if_agreement_fix_required  # Don't allow to add new until booked places fixed
def add_place(request):
    return add_or_edit_place(request, {"title": "Booking - add new camper details"})


@booking_account_required
def edit_place(request, booking_id: int):
    return add_or_edit_place(
        request, {"title": "Booking - edit camper details", "edit_mode": True}, booking_id=booking_id
    )


@booking_account_required
@json_response
def places_json(request):
    account = request.booking_account
    qs = account.bookings.all()
    try:
        exclude_id = int(request.GET["exclude"])
    except (KeyError, ValueError):
        exclude_id = None
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    return {
        "status": "success",
        "places": [booking_to_dict(b) for b in qs],
    }


@booking_account_required
@json_response
def account_json(request):
    return {
        "status": "success",
        "account": account_to_dict(request.booking_account),
    }


@booking_account_optional
@json_response
def place_availability_json(request):
    retval = {"status": "success"}
    camp_id = int(request.GET["camp_id"])
    camp = Camp.objects.get(id=camp_id)
    places = camp.get_places_left()
    retval["result"] = dict(total=places[0], male=places[1], female=places[2])
    return retval


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
def list_bookings(request):
    """
    List bookings a.k.a. checkout
    """
    year = common.get_thisyear()
    now = timezone.now()
    bookings = request.booking_account.bookings.for_year(year).order_by("id").with_prefetch_camp_info()
    # NB - use lists here, not querysets, so that both state_token and book_now
    # functionality apply against same set of bookings.
    basket_bookings = list(bookings.in_basket())
    shelf_bookings = list(bookings.on_shelf())

    if request.method == "POST":
        if "add_another" in request.POST:
            return HttpResponseRedirect(reverse("cciw-bookings-add_place"))

        places = basket_bookings + shelf_bookings
        response = _handle_list_booking_actions(request, places)
        if response:
            return response

        if "book_now" in request.POST:
            state_token = request.POST.get("state_token", "")
            if make_state_token(basket_bookings) != state_token:
                messages.error(
                    request,
                    "Places were not booked due to modifications made "
                    "to the details. Please check the details and try again.",
                )
            else:
                if book_basket_now(basket_bookings):
                    messages.info(request, "Places booked!")
                    return HttpResponseRedirect(reverse("cciw-bookings-pay"))
                else:
                    messages.error(request, "These places cannot be booked for the reasons " "given below.")
        # Start over, because things may have changed.
        return HttpResponseRedirect(request.path)

    # Now apply business rules and other custom processing
    total = Decimal("0.00")
    all_bookable = True
    all_unbookable = True
    agreement_fetcher = AgreementFetcher()
    for booking_list in basket_bookings, shelf_bookings:
        for b in booking_list:
            # decorate object with some attributes to make it easier in template
            b.booking_problems, b.booking_warnings = b.get_booking_problems(agreement_fetcher=agreement_fetcher)
            b.bookable = len(b.booking_problems) == 0
            b.manually_approved = b.state == BookingState.APPROVED

            # Where booking.price_type = PriceType.CUSTOM, and state is not approved,
            # amount_due is meaningless. So we have a new attr, amount_due_normalised
            if b.price_type == PriceType.CUSTOM and b.state != BookingState.APPROVED:
                b.amount_due_normalised = None
            else:
                b.amount_due_normalised = b.amount_due

            # For basket bookings only:
            if not b.shelved:
                if b.bookable:
                    all_unbookable = False
                else:
                    all_bookable = False

                if b.amount_due_normalised is None or total is None:
                    total = None
                else:
                    total = total + b.amount_due_normalised

    discounts = defaultdict(lambda: Decimal("0.00"))
    for b in basket_bookings:
        for name, amount in b.get_available_discounts(now):
            discounts[name] += amount

    if total is not None:
        total_discount = sum(discounts.values())
        grand_total = total - total_discount
    else:
        grand_total = None

    return TemplateResponse(
        request,
        "cciw/bookings/list_bookings.html",
        {
            "title": "Booking - checkout",
            "stage": BookingStage.LIST,
            "basket_bookings": basket_bookings,
            "shelf_bookings": shelf_bookings,
            "all_bookable": all_bookable,
            "all_unbookable": all_unbookable,
            "state_token": make_state_token(basket_bookings),
            "total": total,
            "grand_total": grand_total,
            "discounts_available": discounts.items(),
        },
    )


def _handle_list_booking_actions(request, places):
    def shelve(place):
        place.shelved = True
        place.save()
        messages.info(request, f'Place for "{place.name}" moved to shelf')

    def unshelve(place):
        place.shelved = False
        place.save()
        messages.info(request, f'Place for "{place.name}" moved to basket')

    def delete(place):
        messages.info(request, f'Place for "{place.name}" deleted')
        place.delete()

    def edit(place):
        return HttpResponseRedirect(reverse("cciw-bookings-edit_place", kwargs={"booking_id": str(place.id)}))

    for k in request.POST.keys():
        for r, action in [
            (r"shelve_(\d+)", shelve),
            (r"unshelve_(\d+)", unshelve),
            (r"delete_(\d+)", delete),
            (r"edit_(\d+)", edit),
        ]:
            m = re.match(r, k)
            if m is not None:
                place = None
                with contextlib.suppress(
                    ValueError,  # converting to string
                    IndexError,  # not in list
                ):
                    b_id = int(m.groups()[0])
                    place = [p for p in places if p.id == b_id][0]
                if place is not None:
                    return action(place)


class CustomAmountPayPalForm(PayPalPaymentsForm):
    amount = forms.IntegerField(widget=forms.widgets.NumberInput)


def mk_paypal_form(account, balance, protocol, domain, min_amount=None, max_amount=None):
    paypal_dict = {
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": str(balance),
        "item_name": "Camp place booking",
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
def pay(request):
    acc: BookingAccount = request.booking_account
    this_year = common.get_thisyear()
    price_checker = PriceChecker(expected_years=[b.camp.year for b in acc.bookings.all()] + [this_year])
    balance_due_now = acc.get_balance_due_now(price_checker=price_checker)
    balance_full = acc.get_balance_full(price_checker=price_checker)

    try:
        price_deposit = price_checker.get_deposit_price(this_year)
    except LookupError:
        # This view should be accessible even if prices for the current year are not
        # defined, because people with debts from previous years may need to pay.
        price_deposit = None

    domain = get_current_domain()
    protocol = "https" if request.is_secure() else "http"

    return TemplateResponse(
        request,
        "cciw/bookings/pay.html",
        {
            "stage": BookingStage.PAY,
            "title": "Booking - pay",
            "unconfirmed_places": acc.bookings.for_year(this_year).unconfirmed(),
            "confirmed_places": acc.bookings.for_year(this_year).confirmed(),
            "balance_due_now": balance_due_now,
            "balance_full": balance_full,
            "account_id": acc.id,
            "price_deposit": price_deposit,
            "pending_payment_total": acc.get_pending_payment_total(),
            "paypal_form": mk_paypal_form(acc, balance_due_now, protocol, domain),
            "paypal_form_full": mk_paypal_form(acc, balance_full, protocol, domain),
            "paypal_form_custom": mk_paypal_form(
                acc,
                max(0, balance_due_now),
                protocol,
                domain,
                min_amount=max(balance_due_now, 0),
                max_amount=balance_full,
            ),
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
def account_overview(request):
    if "logout" in request.POST:
        response = HttpResponseRedirect(reverse("cciw-bookings-index"))
        unset_booking_account_cookie(response)
        return response

    account: BookingAccount = request.booking_account
    year = common.get_thisyear()
    bookings = account.bookings.for_year(year)
    price_checker = PriceChecker(expected_years=[b.camp.year for b in bookings])
    agreement_fetcher = AgreementFetcher()

    if request.method == "POST":
        if response := _handle_overview_booking_actions(request, bookings):
            return response

    return TemplateResponse(
        request,
        "cciw/bookings/account_overview.html",
        {
            "title": "Booking - account overview",
            "stage": BookingStage.OVERVIEW,
            "confirmed_places": bookings.confirmed()
            .with_prefetch_camp_info()
            .with_prefetch_missing_agreements(agreement_fetcher),
            "unconfirmed_places": bookings.unconfirmed()
            .with_prefetch_camp_info()
            .with_prefetch_missing_agreements(agreement_fetcher),
            "cancelled_places": bookings.cancelled().with_prefetch_camp_info(),
            "basket_or_shelf": (bookings.in_basket() | bookings.on_shelf()).with_prefetch_camp_info(),
            "balance_due_now": account.get_balance_due_now(price_checker=price_checker),
            "balance_full": account.get_balance_full(price_checker=price_checker),
            "pending_payment_total": account.get_pending_payment_total(),
        },
    )


def _handle_overview_booking_actions(request, bookings):
    fixable_bookings = list(bookings.agreement_fix_required())

    def edit(booking):
        return HttpResponseRedirect(reverse("cciw-bookings-edit_place", kwargs={"booking_id": str(booking.id)}))

    def cancel(booking):
        booking.cancel_and_move_to_shelf()
        messages.info(request, f'Place for "{booking.name}" cancelled and put "on the shelf".')
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
