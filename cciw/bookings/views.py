# == Booking process ==

# = Primary route =
# Step 0 /booking/
#  - shows overview of options, including
#    - get brochure through post
#    - print booking form yourself
#    - book online

# Step 1  /booking/start/
#  - enter email address
#    - must be contact address for person booking
#      "You may want to add 'website@cciw.co.uk' to your known contacts list to
#      ensure our email is not treated as spam"

#  - On POST
#    - if verfied email already in signed cookie then:
#      - if BookingAccount.name already set skip to step 4
#      - otherwise skip to step 3
#
#  - if new account, create in DB
#  - send email verification email
#    - has a link to step 2
#
#  - inform about checking email

# Step 2 /booking/v/
#  - set signed cookie with timestamp, lasting x weeks
#  - redirect to step 3 (or step 4 if already has a name)
#  - redirect to failure message if it went wrong

# Step 3 /booking/account/
#  - enter account name and address
#  - on POST, verify/save and redirect to step 4

# Step 4 /booking/add-place/
#  - enter camper details, including medical details.
#  - serious medical condition
#
#    - Does the camper have any serious physical, mental or behavioural condition
#      that would affect the safety of the camp or our ability to look after him/her?
#
#      This includes, for example, autism and ADHD, significant deafness or
#      blindness, and life-threatening allergies.
#
#      If you answer 'yes', the place will need to be manually approved by a
#      leader before it can be booked. If you do not declare the information where
#      appropriate, we may have to cancel your place or even send a child home,
#      with no refund promised.
#
#  - include field about asking for discount
#    - notify that negotiation of price is possible, but will need to contact
#      booking secretary
#  - includes field about type of place/discount
#  - Business rules about applying for family discount can be checked by looking
#    at all Bookings against BookingAccount for the same year. This still relies
#    on honesty however (one family could book places for another family).
#
#  - on POST, verify/save and redirect to step 5

# Step 5 /booking/places/
#  - check and book
#  - page showing list of places
#    - places to book
#      - if any cannot be booked, this is shown, and the
#        'book now' button is disabled/removed.
#    - places to book later
#    - places already booked, if any
#
#  - places in the 'places to book' list can be deleted or moved
#    to 'book later' list
#
#  - places in the 'book later' list can be deleted or moved
#    to 'places to book' list
#
#  - option to 'add another', goes to step 4
#  - 'book now' button.
#     Processing checks and then books places, or displays reason why places
#     could not be booked. If booking successful, redirect to step 6

# Step 6 /booking/pay/
#  - Amount to pay is calculated
#    - this is just the total amount of all places that are 'booked', from all
#      years, less the 'total amount paid' on the account.
#
#  - user is shown amount and 'Pay now' button, which takes them to Paypal
#  - if amount is zero, obviously do not show 'Pay now'
#  - if amount is negative, they have somehow overpaid.
#
#  - indicate that if they have just paid, it may take a few minutes for
#    the payment to be registered.

# Step 7
#  - Paypal

# Step 8  /booking/complete/
#  - shown 'Thank you' page.

# = Alternative routes =
#
# For cases where the price is changed, we need to be able to go to Step 6
# directly. We need some kind of menu on RHS, that also shows the current
# progress. All steps are links where possible.
#
#  Enter email address (step 1)
#  Account details     (step 3)
#  Booking details     (step 4)
#  Booking summary     (step 5)
#  Payment             (step 6)

# Individual place details can be edited, if the place is
# not confirmed

# = Business logic =
#
# A place can be booked by a user online if:
#
# - either:
#   - state == approved
#     (this is done manually by the booking secretary or leader)
# - or:
#   - the camp has places
#   - no serious medical problem
#   - no custom discount applied for
#   - the discount applied for fits business rules (must check other Bookings in BookingAccount)
#
# Since some of the conditions are time varying (e.g. number of places on camp,
# existence of other Booking objects), we only set 'approved' manually, never
# automatically, since it could become out of date.

# = Complications =
#
# * A user could select the wrong price type (either too much or too little),
#   and it could need to be corrected by an admin, before or after payment is made.
#   So we need to be flexible, and allow a second payment to be made.

# = Admin process =
#
# For dealing with paper bookings, an admin enters essentially the same
# information into the system.
#
# Admin step 1 - account information
#  - covers step 1 to 3 of user process.
#  - requires an AJAX view to retrieve suggestions for the account,
#    which means that a new BookingAccount will not be created
#
# Admin step 2 - booking info
# - covers step 4 to 5 of user process

# Admin payments info
# - 'Add manual payment' form
#   - the amount of the manual payment is entered
#   - includes name/address, with AJAX view to select account
# - 'Add refund payment' form
# - link to general admin page that allows payments to be corrected or deleted
# - (but not added)

# = Leader tools =
#
# Leaders should be able to download a spreadsheet with all current info about
# campers. Sheets:
#  - all campers
#  - boys
#  - girls
#  - birthdays on camps
#
# Leaders need to be presented with a list of bookings that they need to manually
# approve. If they don't approve, need to send email to person booking.

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from functools import wraps
import os
import re

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.http import base36_to_int
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm


from cciw.auth import is_booking_secretary
from cciw.cciwmain.common import get_thisyear, get_current_domain, CciwBaseView, AjaxFormValidation
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp
from cciw.utils.views import user_passes_test_improved

from cciw.bookings.email import send_verify_email, check_email_verification_token
from cciw.bookings.forms import EmailForm, AccountDetailsForm, AddPlaceForm
from cciw.bookings.models import BookingAccount, Price, Booking, book_basket_now, get_early_bird_cutoff_date, early_bird_is_available
from cciw.bookings.models import PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM, \
    BOOKING_INFO_COMPLETE, BOOKING_APPROVED, REQUIRED_PRICE_TYPES, \
    PRICE_DEPOSIT, PRICE_EARLY_BIRD_DISCOUNT


# decorators and utilities

BOOKING_COOKIE_SALT = 'cciw.bookings.BookingAccount cookie'

def set_booking_account_cookie(response, account):
    response.set_signed_cookie('bookingaccount', account.id,
                               salt=BOOKING_COOKIE_SALT,
                               max_age=settings.BOOKING_SESSION_TIMEOUT_SECONDS)


def unset_booking_account_cookie(response):
    response.delete_cookie('bookingaccount')


def get_booking_account_from_cookie(request):
    cookie = request.get_signed_cookie('bookingaccount',
                                       salt=BOOKING_COOKIE_SALT,
                                       default=None,
                                       max_age=settings.BOOKING_SESSION_TIMEOUT_SECONDS)
    if cookie is None:
        return None
    try:
        return BookingAccount.objects.get(id=cookie)
    except BookingAccount.DoesNotExist:
        return None


def ensure_booking_acount_attr(request):
    if not hasattr(request, 'booking_account'):
        request.booking_account = get_booking_account_from_cookie(request)


def booking_account_required(view_func):
    """
    Requires a signed cookie that verifies the booking account,
    redirecting if this is not satisfied,
    and attaches the BookingAccount object to the request.
    """
    @wraps(view_func)
    def view(request, *args, **kwargs):
        ensure_booking_acount_attr(request)
        if request.booking_account is None:
            return HttpResponseRedirect(reverse('cciw.bookings.views.not_logged_in'))
        return view_func(request, *args, **kwargs)
    return view


def account_details_required(view_func):
    @wraps(view_func)
    def view(request, *args, **kwargs):
        ensure_booking_acount_attr(request)
        if not request.booking_account.has_account_details():
            return next_step(request.booking_account)
        return view_func(request, *args, **kwargs)
    return view


booking_secretary_required = user_passes_test_improved(lambda user: user.is_superuser
                                                       or is_booking_secretary(user))


def is_booking_open(year):
    """
    When passed a given year, returns True if booking is open.
    """
    return (Price.objects.filter(year=year, price_type__in=[v for v, d in REQUIRED_PRICE_TYPES]).count()
            == len(REQUIRED_PRICE_TYPES)
            and Camp.objects.filter(year=year).exists())

is_booking_open_thisyear = lambda: is_booking_open(get_thisyear())


# Views

class BookingIndex(CciwBaseView):
    metadata_title = u"Booking"
    template_name = "cciw/bookings/index.html"

    def handle(self, request):
        year = get_thisyear()
        bookingform_relpath = "%s/booking_form_%s.pdf" % (settings.BOOKINGFORMDIR, year)
        context = {}
        if os.path.isfile("%s/%s" % (settings.MEDIA_ROOT, bookingform_relpath)):
            context['bookingform'] = bookingform_relpath
        booking_open = is_booking_open(year)
        if booking_open:
            prices = Price.objects.filter(year=year)
            now = timezone.now()
            early_bird_available = early_bird_is_available(year, now)
            if early_bird_available:
                context['early_bird_available'] = True
                context['early_bird_date'] = get_early_bird_cutoff_date(year)
        else:
            # Show last year's prices
            prices = Price.objects.filter(year=year - 1)

        prices = list(prices.filter(price_type__in=[v for v,d in REQUIRED_PRICE_TYPES]))
        context['booking_open'] = booking_open
        if len(prices) >= len(REQUIRED_PRICE_TYPES):
            getp = lambda v: [p for p in prices if p.price_type == v][0].price
            context['price_full'] = getp(PRICE_FULL)
            context['price_2nd_child'] = getp(PRICE_2ND_CHILD)
            context['price_3rd_child'] = getp(PRICE_3RD_CHILD)
            context['price_deposit'] = getp(PRICE_DEPOSIT)
            context['price_early_bird_discount'] = getp(PRICE_EARLY_BIRD_DISCOUNT)
            if context['early_bird_available']:
                d = getp(PRICE_EARLY_BIRD_DISCOUNT)
                context['price_full_discount'] = getp(PRICE_FULL) - d
                context['price_2nd_child_discount'] = getp(PRICE_2ND_CHILD) - d
                context['price_3rd_child_discount'] = getp(PRICE_3RD_CHILD) - d
        return self.render(context)


def next_step(account):
    if account.has_account_details():
        if account.bookings.for_year(get_thisyear()).in_basket().exists():
            return HttpResponseRedirect(reverse('cciw.bookings.views.list_bookings'))
        else:
            return HttpResponseRedirect(reverse('cciw.bookings.views.add_place'))
    else:
        return HttpResponseRedirect(reverse('cciw.bookings.views.account_details'))


class BookingLogInBase(CciwBaseView):
    metadata_title = u"Booking - log in"
    magic_context = {'stage': 'login'}


class BookingStart(BookingLogInBase):
    form_class = EmailForm
    template_name = 'cciw/bookings/start.html'
    magic_context = {'booking_open': is_booking_open_thisyear}

    def handle(self, request, *args, **kwargs):
        account = get_booking_account_from_cookie(request)
        if account is not None:
            return next_step(account)
        if request.method == "POST":
            form = self.form_class(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                try:
                    account = BookingAccount.objects.filter(email__iexact=email)[0]
                except IndexError:
                    # Ensure we use NULLs, not empty strings, or we will not be able to
                    # create more than one, as they will have same 'name and post_code'
                    account = BookingAccount.objects.create(email=email,
                                                    name=None,
                                                    post_code=None)
                send_verify_email(self.request, account)
                return HttpResponseRedirect(reverse_lazy('cciw.bookings.views.email_sent'))
        else:
            form = self.form_class()

        return self.render({'form': form})


class BookingEmailSent(BookingLogInBase):
    template_name = "cciw/bookings/email_sent.html"


def verify_email(request, account_id, token, action):
    fail = lambda: HttpResponseRedirect(reverse('cciw.bookings.views.verify_email_failed'))
    try:
        account_id = base36_to_int(account_id)
    except ValueError:
        return fail()
    try:
        account = BookingAccount.objects.get(id=account_id)
    except BookingAccount.DoesNotExist:
        return fail()

    if check_email_verification_token(account, token):
        return action(account)
    else:
        return fail()


def verify_email_and_start(request, account_id, token):
    def action(account):
        now = timezone.now()
        last_login = account.last_login

        if account.first_login is None:
            account.first_login = now
        account.last_login = now
        account.save()

        if last_login is not None and (now - last_login) > \
                timedelta(30*6): # six months
            resp = HttpResponseRedirect(reverse('cciw.bookings.views.account_details'))
            set_booking_account_cookie(resp, account)
            messages.info(request, "Welcome back! Please check and update your account details")
            return resp

        resp = next_step(account)
        set_booking_account_cookie(resp, account)
        messages.info(request, u"Logged in!")
        return resp

    return verify_email(request, account_id, token,
                        action)


def verify_email_and_pay(request, account_id, token):
    def action(account):
        resp = HttpResponseRedirect(reverse('cciw.bookings.views.pay'))
        set_booking_account_cookie(resp, account)
        return resp

    return verify_email(request, account_id, token,
                        action)


class BookingVerifyEmailFailed(BookingLogInBase):
    metadata_title = u"Booking - account email verification failed"
    template_name = "cciw/bookings/email_verification_failed.html"


class BookingNotLoggedIn(CciwBaseView):
    metadata_title = u"Booking - not logged in"
    template_name = "cciw/bookings/not_logged_in.html"


class BookingAccountDetails(CciwBaseView, AjaxFormValidation):
    metadata_title = u"Booking - account details"
    form_class = AccountDetailsForm
    template_name = 'cciw/bookings/account_details.html'
    magic_context = {'stage': 'account'}

    def handle(self, request):
        if request.method == "POST":
            form = self.form_class(request.POST, instance=self.request.booking_account)
            if form.is_valid():
                form.save()
                messages.info(self.request, u'Account details updated, thank you.')
                return HttpResponseRedirect(reverse('cciw.bookings.views.add_place'))
        else:
            form = self.form_class(instance=self.request.booking_account)
        return self.render({'form': form})


class BookingEditAddBase(CciwBaseView, AjaxFormValidation):
    template_name = 'cciw/bookings/add_place.html'
    form_class = AddPlaceForm
    magic_context = {'booking_open': is_booking_open_thisyear,
                     'stage': 'place'}

    def handle(self, request, *args, **kwargs):
        year = get_thisyear()
        now = timezone.now()

        if request.method == "POST" and not is_booking_open_thisyear():
            # Redirect to same view, but GET
            return HttpResponseRedirect(request.get_full_path())

        if 'id' in kwargs:
            # Edit
            try:
                booking = self.request.booking_account.bookings.get(id=int(kwargs['id']))
            except (ValueError, Booking.DoesNotExist):
                raise Http404
            if request.method == "POST" and not booking.is_user_editable():
                # Redirect to same view, but GET
                return HttpResponseRedirect(request.get_full_path())
            new_booking = False
        else:
            # Add
            booking = None
            new_booking = True

        if request.method == "POST":
            form = self.form_class(request.POST, instance=booking)
            if form.is_valid():
                form.instance.account = self.request.booking_account
                form.instance.auto_set_amount_due()
                form.instance.state = BOOKING_INFO_COMPLETE
                if new_booking:
                    form.instance.created_online = True
                form.save()

                messages.info(self.request, u'Details for "%s" were saved successfully' % form.instance.name)
                return HttpResponseRedirect(reverse('cciw.bookings.views.list_bookings'))
        else:
            form = self.form_class(instance=booking)

        c = {'form':form,
             'early_bird_available': early_bird_is_available(year, now),
             'early_bird_date': get_early_bird_cutoff_date(year),
             'price_early_bird_discount': lambda: Price.objects.get(year=year, price_type=PRICE_EARLY_BIRD_DISCOUNT).price,
             }
        if booking is not None and not booking.is_user_editable():
            c['read_only'] = True
        return self.render(c)


class BookingAddPlace(BookingEditAddBase):
    metadata_title = u"Booking - add new camper details"


class BookingEditPlace(BookingEditAddBase):
    metadata_title = u"Booking - edit camper details"


# Public attributes - i.e. that the account holder is allowed to see
BOOKING_PLACE_PUBLIC_ATTRS = [
    'id',
    'first_name',
    'last_name',
    'sex',
    'date_of_birth',
    'address',
    'post_code',
    'phone_number',
    'church',
    'contact_address',
    'contact_post_code',
    'contact_phone_number',
    'dietary_requirements',
    'gp_name',
    'gp_address',
    'gp_phone_number',
    'medical_card_number',
    'last_tetanus_injection',
    'allergies',
    'regular_medication_required',
    'learning_difficulties',
    'serious_illness',
    'created',
]

# Public attributes - i.e. that the account holder is allowed to see
ACCOUNT_PUBLIC_ATTRS = [
    'email',
    'name',
    'address',
    'post_code',
    'phone_number',
]

booking_to_dict = lambda b: dict((k, getattr(b, k)) for k in BOOKING_PLACE_PUBLIC_ATTRS)
account_to_dict = lambda acc: dict((k, getattr(acc, k))
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
        try:
            exclude_id = int(request.GET['exclude'])
            qs = qs.exclude(id=exclude_id)
        except ValueError:
            pass
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
    try:
        data['created'] = data['created_0'] + ' ' + data['created_1']
    except KeyError:
        pass


    if 'booking_id' in data:
        booking_obj = Booking.objects.get(id=int(data['booking_id']))
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
            retval['problems'] = ['Prices have not been set for the year %d' % instance.camp.year]
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


@csrf_exempt
@json_response
def get_expected_amount_due(request):
    fail = {'status':'success',
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

    except (ValueError, KeyError): # not a valid price_type/camp, data missing
        return fail
    try:
        amount = b.expected_amount_due()
    except Price.DoesNotExist:
        return fail

    if amount is not None:
        amount = str(amount) # convert decimal
    return {'status': 'success',
            'amount': amount}


def make_state_token(bookings):
    # Hash some key data about booking, without which the booking isn't valid.
    bookings.sort(key=lambda b: b.id)
    data = u'|'.join([u':'.join(map(str, [b.id, b.camp.id, b.amount_due, b.name, b.price_type, b.state]))
                     for b in bookings])
    return salted_hmac('cciw.bookings.state_token', data.encode('utf-8')).hexdigest()


class BookingListBookings(CciwBaseView):
    metadata_title = "Booking - checkout"
    template_name = "cciw/bookings/list_bookings.html"
    magic_context = {'stage': 'list'}

    def handle(self, request):
        year = get_thisyear()
        now = timezone.now()
        bookings = request.booking_account.bookings
        # NB - use lists here, not querysets, so that both state_token and book_now
        # functionality apply against same set of bookings.
        basket_bookings = list(bookings.for_year(year).in_basket())
        shelf_bookings = list(bookings.for_year(year).on_shelf())

        if request.method == "POST":
            if 'add_another' in request.POST:
                return HttpResponseRedirect(reverse('cciw.bookings.views.add_place'))

            places = basket_bookings + shelf_bookings

            def shelve(place):
                place.shelved = True
                place.save()
                messages.info(request, u'Place for "%s" moved to shelf' % place.name)

            def unshelve(place):
                place.shelved = False
                place.save()
                messages.info(request, u'Place for "%s" moved to basket' % place.name)

            def delete(place):
                messages.info(request, u'Place for "%s" deleted' % place.name)
                place.delete()

            def edit(place):
                return HttpResponseRedirect(reverse('cciw.bookings.views.edit_place',
                                                    kwargs={'id':str(place.id)}))

            for k in request.POST.keys():
                # handle shelve and unshelve buttons
                for r, action in [(r'shelve_(\d+)', shelve),
                                  (r'unshelve_(\d+)', unshelve),
                                  (r'delete_(\d+)', delete),
                                  (r'edit_(\d+)', edit),
                                  ]:
                    m = re.match(r, k)
                    if m is not None:
                        try:
                            b_id = int(m.groups()[0])
                            place = [p for p in places if p.id == b_id][0]
                            retval = action(place)
                            if retval is not None:
                                return retval
                        except (ValueError, # converting to string
                                IndexError, # not in list
                                ):
                            pass

            if 'book_now' in request.POST:
                state_token = request.POST.get('state_token', '')
                if make_state_token(basket_bookings) != state_token:
                    messages.error(request, u"Places were not booked due to modifications made "
                                   u"to the details. Please check the details and try again.")
                else:
                    if book_basket_now(basket_bookings):
                        messages.info(request, u"Places booked!")
                        return HttpResponseRedirect(reverse('cciw.bookings.views.pay'))
                    else:
                        messages.error(request, u"These places cannot be booked for the reasons "
                                       u"given below.")
            # Start over, because things may have changed.
            return HttpResponseRedirect(request.path)

        # Now apply business rules and other custom processing
        total = Decimal('0.00')
        all_bookable = True
        all_unbookable = True
        for l in basket_bookings, shelf_bookings:
            for b in l:
                # decorate object with some attributes to make it easier in template
                b.booking_problems, b.booking_warnings = b.get_booking_problems()
                b.bookable = len(b.booking_problems) == 0
                b.manually_approved = b.state == BOOKING_APPROVED

                # Where booking.price_type = PRICE_CUSTOM, and state is not approved,
                # amount_due is meaningless. So we have a new attr, amount_due_normalised
                if b.price_type == PRICE_CUSTOM and b.state != BOOKING_APPROVED:
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

        c = {
            'basket_bookings': basket_bookings,
            'shelf_bookings': shelf_bookings,
            'all_bookable': all_bookable,
            'all_unbookable': all_unbookable,
            'state_token': make_state_token(basket_bookings),
            'total': total,
            'grand_total': grand_total,
            'discounts_available': discounts.items(),
        }
        return self.render(c)


def mk_paypal_form(account, balance, protocol, domain):
    paypal_dict = {
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": str(balance),
        "item_name": u"Camp place booking",
        "invoice": "%s-%s-%s" % (account.id, balance,
                                 timezone.now()), # We don't need this, but must be unique
        "notify_url":  "%s://%s%s" % (protocol, domain, reverse('paypal-ipn')),
        "return_url": "%s://%s%s" % (protocol, domain, reverse('cciw.bookings.views.pay_done')),
        "cancel_return": "%s://%s%s" % (protocol, domain, reverse('cciw.bookings.views.pay_cancelled')),
        "custom": "account:%s;" % str(account.id),
        "currency_code": "GBP",
        "no_note": "1",
        "no_shipping": "1",
        }
    return PayPalPaymentsForm(initial=paypal_dict)


class BookingPayBase(CciwBaseView):
    magic_context = {'stage': 'pay'}


class BookingPay(BookingPayBase):
    metadata_title = "Booking - pay"
    template_name = "cciw/bookings/pay.html"

    def handle(self, request):
        acc = self.request.booking_account
        balance_due = acc.get_balance(allow_deposits=True)
        balance_full = acc.get_balance(allow_deposits=False)

        # This view should be accessible even if prices for the current year are
        # not defined.
        price_deposit = list(Price.objects.filter(year=get_thisyear(), price_type=PRICE_DEPOSIT))
        if len(price_deposit) == 0:
            price_deposit = None
        else:
            price_deposit = price_deposit[0].price

        domain = get_current_domain()
        protocol = 'https' if self.request.is_secure() else 'http'

        c = {
            'unconfirmed_places': acc.bookings.unconfirmed(),
            'balance_due': balance_due,
            'balance_full': balance_full,
            'account_id': acc.id,
            'price_deposit': price_deposit,
            'paypal_form': mk_paypal_form(acc, balance_due, protocol, domain),
            'paypal_form_full': mk_paypal_form(acc, balance_full, protocol, domain),
        }
        return self.render(c)


class BookingPayDone(BookingPayBase):
    metadata_title = u"Booking - payment complete"
    template_name = "cciw/bookings/pay_done.html"


class BookingPayCancelled(BookingPayBase):
    metadata_title = u"Booking - payment cancelled"
    template_name = "cciw/bookings/pay_cancelled.html"


class BookingAccountOverview(CciwBaseView):
    metadata_title = u"Booking - account overview"
    template_name = 'cciw/bookings/account_overview.html'

    def handle(self, request):
        if 'logout' in request.POST:
            response = HttpResponseRedirect(reverse('cciw.bookings.views.index'))
            unset_booking_account_cookie(response)
            return response

        c = {}
        acc = self.request.booking_account
        year = get_thisyear()
        bookings = acc.bookings.for_year(year)
        c['confirmed_places'] = bookings.confirmed()
        c['unconfirmed_places'] = bookings.unconfirmed()
        c['cancelled_places'] = bookings.cancelled()
        c['basket'] = bookings.in_basket()
        c['shelf'] = bookings.on_shelf().exists()
        c['stage'] = ''
        return self.render(c)


index = BookingIndex.as_view()
start = BookingStart.as_view()
email_sent = BookingEmailSent.as_view()
verify_email_failed = BookingVerifyEmailFailed.as_view()
account_details = booking_account_required(BookingAccountDetails.as_view())
not_logged_in = BookingNotLoggedIn.as_view()
add_place = booking_account_required(account_details_required(BookingAddPlace.as_view()))
edit_place = booking_account_required(account_details_required(BookingEditPlace.as_view()))
list_bookings = booking_account_required(BookingListBookings.as_view())
pay = booking_account_required(BookingPay.as_view())
pay_done = csrf_exempt(BookingPayDone.as_view()) # PayPal will post to this, need csrf_exempt
pay_cancelled = csrf_exempt(BookingPayCancelled.as_view()) # PayPal will post to this
account_overview = booking_account_required(BookingAccountOverview.as_view())
