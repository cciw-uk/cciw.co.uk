import contextlib
import os
import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import csrf_exempt
from django_countries.fields import Country
from paypal.standard.forms import PayPalPaymentsForm

from cciw.bookings.email import send_verify_email
from cciw.bookings.forms import AccountDetailsForm, AddPlaceForm, EmailForm
from cciw.bookings.middleware import get_booking_account_from_request, unset_booking_account_cookie
from cciw.bookings.models import (AgreementFetcher, Booking, BookingAccount, BookingState, CustomAgreement, Price,
                                  PriceChecker, PriceType, any_bookings_possible, book_basket_now,
                                  build_paypal_custom_field, early_bird_is_available, get_early_bird_cutoff_date,
                                  is_booking_open, is_booking_open_thisyear)
from cciw.cciwmain import common
from cciw.cciwmain.common import ajax_form_validate, get_current_domain
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp
from cciw.utils.views import user_passes_test_improved

# decorators and utilities


class BookingStage:
    LOGIN = 'login'
    ACCOUNT = 'account'
    OVERVIEW = 'overview'
    PLACE = 'place'
    LIST = 'list'
    PAY = 'pay'


def ensure_booking_account_attr(request):
    if not hasattr(request, 'booking_account'):
        request.booking_account = get_booking_account_from_request(request)


def booking_account_required(view_func):
    """
    Requires a signed cookie that verifies the booking account,
    redirecting if this is not satisfied,
    and attaches the BookingAccount object to the request.
    """
    @wraps(view_func)
    def view(request, *args, **kwargs):
        ensure_booking_account_attr(request)
        if request.booking_account is None:
            return HttpResponseRedirect(reverse('cciw-bookings-not_logged_in'))
        return view_func(request, *args, **kwargs)
    return view


def account_details_required(view_func):
    @wraps(view_func)
    def view(request, *args, **kwargs):
        ensure_booking_account_attr(request)
        if not request.booking_account.has_account_details():
            return next_step(request.booking_account)
        return view_func(request, *args, **kwargs)
    return view


booking_secretary_required = user_passes_test_improved(lambda user:
                                                       user.is_superuser or
                                                       user.is_booking_secretary)


# Views

def index(request):
    ensure_booking_account_attr(request)
    year = common.get_thisyear()
    bookingform_relpath = f"{settings.BOOKINGFORMDIR}/booking_form_{year}.pdf"
    context = {
        'title': 'Booking',
    }
    if os.path.isfile(f"{settings.MEDIA_ROOT}/{bookingform_relpath}"):
        context['bookingform'] = bookingform_relpath
    booking_open = is_booking_open(year)
    if booking_open:
        prices = Price.objects.for_year(year)
        now = timezone.now()
        early_bird_available = early_bird_is_available(year, now)
        context['early_bird_available'] = early_bird_available
        context['early_bird_date'] = get_early_bird_cutoff_date(year)
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
        ('Full price', getp(PriceType.FULL)),
        ('2nd camper from the same family', getp(PriceType.SECOND_CHILD)),
        ('Subsequent children from the same family', getp(PriceType.THIRD_CHILD))
    ]
    if any(p is None for caption, p in price_list):
        price_list = []
    # Add discounts:
    price_list = [(caption, p, p - early_bird_discount if early_bird_discount is not None else 0)
                  for caption, p in price_list]

    context.update({
        'price_list': price_list,
        'price_deposit': getp(PriceType.DEPOSIT),
        'price_early_bird_discount': early_bird_discount,
        'booking_open': booking_open,
        'any_bookings_possible': any_bookings_possible(common.get_thisyear()),
        'full_payment_due_time': settings.BOOKING_FULL_PAYMENT_DUE_TIME,
    })
    return TemplateResponse(request, 'cciw/bookings/index.html', context)


def next_step(account):
    """
    Returns a redirect to the next obvious step for this account.
    """
    if account.has_account_details():
        bookings = account.bookings.for_year(common.get_thisyear())
        if (bookings.in_basket() | bookings.on_shelf() | bookings.booked()).exists():
            return HttpResponseRedirect(reverse('cciw-bookings-account_overview'))
        else:
            return HttpResponseRedirect(reverse('cciw-bookings-add_place'))
    else:
        return HttpResponseRedirect(reverse('cciw-bookings-account_details'))


def start(request):
    form_class = EmailForm
    account = get_booking_account_from_request(request)
    if account is not None:
        return next_step(account)
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            send_verify_email(request, email)
            return HttpResponseRedirect(reverse('cciw-bookings-email_sent'))
    else:
        form = form_class()

    return TemplateResponse(request, 'cciw/bookings/start.html', {
        'stage': BookingStage.LOGIN,
        'title': 'Booking - log in',
        'booking_open': is_booking_open_thisyear(),
        'form': form,
        'any_bookings_possible': any_bookings_possible(common.get_thisyear()),
    })


def email_sent(request):
    return TemplateResponse(request, 'cciw/bookings/email_sent.html', {
        'stage': BookingStage.LOGIN,
        'title': 'Booking - log in',
    })


def link_expired_email_sent(request):
    return TemplateResponse(request, 'cciw/bookings/email_sent.html', {
        'stage': BookingStage.LOGIN,
        'title': 'Booking - log in',
        'link_expired': True,
    })


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

    if last_login is not None and (
            (now - last_login) > timedelta(30 * 6)):  # six months
        messages.info(request, "Welcome back! Please check and update your account details")
        return HttpResponseRedirect(reverse('cciw-bookings-account_details'))
    else:
        return next_step(account)


def verify_email_failed(request):
    return TemplateResponse(request, 'cciw/bookings/email_verification_failed.html', {
        'stage': BookingStage.LOGIN,
        'title': 'Booking - account email verification failed',
    })


def not_logged_in(request):
    return TemplateResponse(request, 'cciw/bookings/not_logged_in.html', {
        'title': 'Booking - not logged in',
    })


@booking_account_required
@ajax_form_validate(AccountDetailsForm)
def account_details(request):
    form_class = AccountDetailsForm

    if request.method == "POST":
        form = form_class(request.POST, instance=request.booking_account)
        if form.is_valid():
            form.save()
            messages.info(request, 'Account details updated, thank you.')
            return next_step(request.booking_account)
    else:
        form = form_class(instance=request.booking_account)
    return TemplateResponse(request, 'cciw/bookings/account_details.html', {
        'title': 'Booking - account details',
        'stage': BookingStage.ACCOUNT,
        'form': form,
    })


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
        except (ValueError, Booking.DoesNotExist):
            raise Http404
        if request.method == "POST" and not booking.is_user_editable():
            # Redirect to same view, but GET
            return HttpResponseRedirect(request.get_full_path())
    else:
        # Add
        booking = None

    custom_agreements = CustomAgreement.objects.for_year(year)
    if request.method == "POST":
        form = form_class(request.POST, instance=booking)
        if form.is_valid():
            booking: Booking = form.instance
            custom_agreements_checked = [
                agreement
                for agreement in custom_agreements
                if f'custom_agreement_{agreement.id}' in request.POST
            ]
            booking.save_for_account(request.booking_account, custom_agreements=custom_agreements_checked)
            messages.info(request, f'Details for "{booking.name}" were saved successfully')
            return HttpResponseRedirect(reverse('cciw-bookings-list_bookings'))
    else:
        form = form_class(instance=booking)

    context.update({
        'booking_open': is_booking_open_thisyear(),
        'stage': BookingStage.PLACE,
        'form': form,
        'early_bird_available': early_bird_is_available(year, now),
        'early_bird_date': get_early_bird_cutoff_date(year),
        'price_early_bird_discount': lambda: Price.objects.get(year=year, price_type=PriceType.EARLY_BIRD_DISCOUNT).price,
        'read_only': booking is not None and not booking.is_user_editable(),
        'custom_agreements': custom_agreements,
    })
    return TemplateResponse(request, 'cciw/bookings/add_place.html', context)


def add_place(request):
    return add_or_edit_place(request, {'title': 'Booking - add new camper details'})


def edit_place(request, booking_id):
    return add_or_edit_place(request, {'title': 'Booking - edit camper details', 'edit_mode': True},
                             booking_id=booking_id)


# Public attributes - i.e. that the account holder is allowed to see
BOOKING_PLACE_PUBLIC_ATTRS = [
    'id',
    'first_name',
    'last_name',
    'sex',
    'date_of_birth',
    'address_line1',
    'address_line2',
    'address_city',
    'address_county',
    'address_country',
    'address_post_code',
    'phone_number',
    'church',
    'contact_name',
    'contact_line1',
    'contact_line2',
    'contact_city',
    'contact_county',
    'contact_country',
    'contact_post_code',
    'contact_phone_number',
    'dietary_requirements',
    'gp_name',
    'gp_line1',
    'gp_line2',
    'gp_city',
    'gp_county',
    'gp_country',
    'gp_post_code',
    'gp_phone_number',
    'medical_card_number',
    'last_tetanus_injection_date',
    'allergies',
    'regular_medication_required',
    'learning_difficulties',
    'serious_illness',
    'created_at',
]

# Public attributes - i.e. that the account holder is allowed to see
ACCOUNT_PUBLIC_ATTRS = [
    'email',
    'name',
    'address_line1',
    'address_line2',
    'address_city',
    'address_county',
    'address_country',
    'address_post_code',
    'phone_number',
]

handle_country = lambda v: v.code if isinstance(v, Country) else v
booking_to_dict = lambda b: dict((k, handle_country(getattr(b, k))) for k in BOOKING_PLACE_PUBLIC_ATTRS)
account_to_dict = lambda acc: dict((k, handle_country(getattr(acc, k)))
                                   for k in ACCOUNT_PUBLIC_ATTRS)


@booking_account_required
@json_response
def places_json(request):
    return _get_places_dict(request, request.booking_account)


@booking_secretary_required
@json_response
def all_places_json(request):
    try:
        account_id = int(request.GET['id'])
    except (KeyError, ValueError):
        return {'status': 'success',
                'places': []}
    acc = BookingAccount.objects.get(id=account_id)
    return _get_places_dict(request, acc)


def _get_places_dict(request, account):
    retval = {'status': 'success'}
    qs = account.bookings.all()
    if 'exclude' in request.GET:
        with contextlib.suppress(ValueError):
            exclude_id = int(request.GET['exclude'])
            qs = qs.exclude(id=exclude_id)
    retval['places'] = [booking_to_dict(b) for b in qs]
    return retval


@booking_account_required
@json_response
def account_json(request):
    return _get_account_dict(request.booking_account)


@booking_secretary_required
@json_response
def all_accounts_json(request):
    try:
        account_id = int(request.GET['id'])
    except (KeyError, ValueError):
        return {'status': 'failure'}
    acc = BookingAccount.objects.get(id=account_id)
    return _get_account_dict(acc)


def _get_account_dict(account):
    retval = {'status': 'success'}
    retval['account'] = account_to_dict(account)
    return retval


@booking_secretary_required
@json_response
def booking_problems_json(request):
    """
    Get the booking problems associated with the data POSTed.
    """
    # This is used by the admin.
    # We have to create a Booking object, but not save it.
    from .admin import BookingAdminForm

    # Make it easy on front end:
    data = request.POST.copy()
    with contextlib.suppress(KeyError):
        data['created_at'] = data['created_at_0'] + ' ' + data['created_at_1']

    if 'booking_id' in data:
        booking_obj = Booking.objects.get(id=int(data['booking_id']))
        if 'created_online' not in data:
            # readonly field, data not included in form
            data['created_online'] = booking_obj.created_online
        form = BookingAdminForm(data, instance=booking_obj)
    else:
        form = BookingAdminForm(data)

    retval = {'status': 'success'}
    if form.is_valid():
        retval['valid'] = True
        instance = form.save(commit=False)
        # We will get errors later on if prices don't exist for the year chosen, so
        # we check that first.
        if not is_booking_open(instance.camp.year):
            retval['problems'] = [f'Prices have not been set for the year {instance.camp.year}']
        else:
            problems, warnings = instance.get_booking_problems(booking_sec=True)
            retval['problems'] = problems + warnings
    else:
        retval['valid'] = False
        retval['errors'] = form.errors
    return retval


@json_response
def place_availability_json(request):
    retval = {'status': 'success'}
    camp_id = int(request.GET['camp_id'])
    camp = Camp.objects.get(id=camp_id)
    places = camp.get_places_left()
    retval['result'] = dict(total=places[0],
                            male=places[1],
                            female=places[2])
    return retval


@json_response
@staff_member_required
@booking_secretary_required
def get_expected_amount_due(request):
    fail = {'status': 'success',
            'amount': None}
    try:
        # If we use a form to construct an object, we won't get pass
        # validation. So we construct a partial object, doing manual parsing of
        # posted vars.

        if 'id' in request.POST:
            # Start with saved data if it is available
            b = Booking.objects.get(id=int(request.POST['id']))
        else:
            b = Booking()
        b.price_type = int(request.POST['price_type'])
        b.camp_id = int(request.POST['camp'])
        b.early_bird_discount = 'early_bird_discount' in request.POST
        b.state = int(request.POST['state'])
    except (ValueError, KeyError):  # not a valid price_type/camp, data missing
        return fail
    try:
        amount = b.expected_amount_due()
    except Price.DoesNotExist:
        return fail

    if amount is not None:
        amount = str(amount)  # convert decimal
    return {'status': 'success',
            'amount': amount}


def make_state_token(bookings):
    # Hash some key data about booking, without which the booking isn't valid.
    # This is a protection mechanism for the user's benefit, to ensure they
    # don't accidentally book something significantly different from what they
    # expect (due to, for example, changing a booking in a different tab). For
    # this reason we don't need all info.
    data = '|'.join([':'.join(map(str, [b.id, b.camp.id, b.amount_due, b.name, b.price_type, b.state]))
                     for b in sorted(bookings, key=lambda b: b.id)])
    return salted_hmac('cciw.bookings.state_token', data.encode('utf-8')).hexdigest()


@booking_account_required
def list_bookings(request):
    year = common.get_thisyear()
    now = timezone.now()
    bookings = request.booking_account.bookings.for_year(year).order_by('id')
    # NB - use lists here, not querysets, so that both state_token and book_now
    # functionality apply against same set of bookings.
    basket_bookings = list(bookings.in_basket())
    shelf_bookings = list(bookings.on_shelf())

    if request.method == "POST":
        if 'add_another' in request.POST:
            return HttpResponseRedirect(reverse('cciw-bookings-add_place'))

        places = basket_bookings + shelf_bookings
        response = _handle_list_booking_actions(request, places)
        if response:
            return response

        if 'book_now' in request.POST:
            state_token = request.POST.get('state_token', '')
            if make_state_token(basket_bookings) != state_token:
                messages.error(request, "Places were not booked due to modifications made "
                               "to the details. Please check the details and try again.")
            else:
                if book_basket_now(basket_bookings):
                    messages.info(request, "Places booked!")
                    return HttpResponseRedirect(reverse('cciw-bookings-pay'))
                else:
                    messages.error(request, "These places cannot be booked for the reasons "
                                   "given below.")
        # Start over, because things may have changed.
        return HttpResponseRedirect(request.path)

    # Now apply business rules and other custom processing
    total = Decimal('0.00')
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

    discounts = defaultdict(lambda: Decimal('0.00'))
    for b in basket_bookings:
        for name, amount in b.get_available_discounts(now):
            discounts[name] += amount

    if total is not None:
        total_discount = sum(discounts.values())
        grand_total = total - total_discount
    else:
        grand_total = None

    return TemplateResponse(request, 'cciw/bookings/list_bookings.html', {
        'title': 'Booking - checkout',
        'stage': BookingStage.LIST,
        'basket_bookings': basket_bookings,
        'shelf_bookings': shelf_bookings,
        'all_bookable': all_bookable,
        'all_unbookable': all_unbookable,
        'state_token': make_state_token(basket_bookings),
        'total': total,
        'grand_total': grand_total,
        'discounts_available': discounts.items(),
    })


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
        return HttpResponseRedirect(reverse('cciw-bookings-edit_place',
                                            kwargs={'booking_id': str(place.id)}))

    for k in request.POST.keys():
        for r, action in [(r'shelve_(\d+)', shelve),
                          (r'unshelve_(\d+)', unshelve),
                          (r'delete_(\d+)', delete),
                          (r'edit_(\d+)', edit),
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
                    retval = action(place)
                    if retval is not None:
                        return retval


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
        form.fields['amount'].widget.attrs.update(
            {'min': str(min_amount),
             'value': str(min_amount)})

    if max_amount is not None:
        form.fields['amount'].widget.attrs['max'] = str(max_amount)

    return form


@booking_account_required
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
    protocol = 'https' if request.is_secure() else 'http'

    return TemplateResponse(request, 'cciw/bookings/pay.html', {
        'stage': BookingStage.PAY,
        'title': 'Booking - pay',
        'unconfirmed_places': acc.bookings.for_year(this_year).unconfirmed(),
        'confirmed_places': acc.bookings.for_year(this_year).confirmed(),
        'balance_due_now': balance_due_now,
        'balance_full': balance_full,
        'account_id': acc.id,
        'price_deposit': price_deposit,
        'pending_payment_total': acc.get_pending_payment_total(),
        'paypal_form': mk_paypal_form(acc, balance_due_now, protocol, domain),
        'paypal_form_full': mk_paypal_form(acc, balance_full, protocol, domain),
        'paypal_form_custom': mk_paypal_form(acc,
                                             max(0, balance_due_now),
                                             protocol, domain,
                                             min_amount=max(balance_due_now, 0),
                                             max_amount=balance_full)
    })


@csrf_exempt  # PayPal will post to this
def pay_done(request):
    return TemplateResponse(request, 'cciw/bookings/pay_done.html', {
        'title': 'Booking - payment complete',
        'stage': BookingStage.PAY,
    })


@csrf_exempt  # PayPal will post to this
def pay_cancelled(request):
    return TemplateResponse(request, 'cciw/bookings/pay_cancelled.html', {
        'title': 'Booking - payment cancelled',
        'stage': BookingStage.PAY,
    })


@booking_account_required
def account_overview(request):
    if 'logout' in request.POST:
        response = HttpResponseRedirect(reverse('cciw-bookings-index'))
        unset_booking_account_cookie(response)
        return response

    account: BookingAccount = request.booking_account
    year = common.get_thisyear()
    bookings = account.bookings.for_year(year)
    price_checker = PriceChecker(expected_years=[b.camp.year for b in bookings])
    return TemplateResponse(request, 'cciw/bookings/account_overview.html', {
        'title': 'Booking - account overview',
        'stage': BookingStage.OVERVIEW,
        'confirmed_places': bookings.confirmed(),
        'unconfirmed_places': bookings.unconfirmed(),
        'cancelled_places': bookings.cancelled(),
        'basket_or_shelf': (bookings.in_basket() | bookings.on_shelf()),
        'balance_due_now': account.get_balance_due_now(price_checker=price_checker),
        'balance_full': account.get_balance_full(price_checker=price_checker),
        'pending_payment_total': account.get_pending_payment_total(),
    })


class BookingAccountAutocomplete(autocomplete.Select2QuerySetView):
    search_fields = ['name']

    def get_queryset(self):
        request = self.request
        if request.user.is_authenticated and request.user.is_booking_secretary:
            return BookingAccount.objects.order_by('name', 'address_post_code').filter(name__icontains=self.q)
        else:
            return BookingAccount.objects.none()
