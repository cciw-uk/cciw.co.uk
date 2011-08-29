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
# - 'Add cheque payment' form
#   - the amount of the cheque payment is entered (and cheque number?)
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

from datetime import datetime
from decimal import Decimal
from functools import wraps
import os
import re

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect, Http404
from django.views.generic.base import TemplateView, TemplateResponseMixin
from django.views.generic.edit import ProcessFormView, FormMixin, ModelFormMixin, BaseUpdateView, BaseCreateView

from cciw.cciwmain.common import get_thisyear, DefaultMetaData, AjaxyFormMixin
from cciw.cciwmain.decorators import json_response
from cciw.cciwmain.models import Camp

from cciw.bookings.email import send_verify_email, check_email_verification_token
from cciw.bookings.forms import EmailForm, AccountDetailsForm, AddPlaceForm
from cciw.bookings.models import BookingAccount, Price, Booking
from cciw.bookings.models import PRICE_FULL, PRICE_2ND_CHILD, PRICE_3RD_CHILD, PRICE_CUSTOM, \
    BOOKING_INFO_COMPLETE, BOOKING_APPROVED, VALUED_PRICE_TYPES, PRICE_SOUTH_WALES_TRANSPORT


# decorators and utilities

BOOKING_COOKIE_SALT = 'cciw.bookings.BookingAccount cookie'

def set_booking_account_cookie(response, account):
    response.set_signed_cookie('bookingaccount', account.id,
                               salt=BOOKING_COOKIE_SALT,
                               max_age=settings.BOOKING_SESSION_TIMEOUT_SECONDS)


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


def booking_account_required(view_func):
    """
    Requires a signed cookie that verifies the booking account,
    redirecting if this is not satisfied,
    and attaches the BookingAccount object to the request.
    """
    @wraps(view_func)
    def view(request, *args, **kwargs):
        account = get_booking_account_from_cookie(request)
        if account is None:
            return HttpResponseRedirect(reverse('cciw.bookings.views.not_logged_in'))
        request.booking_account = account
        return view_func(request, *args, **kwargs)
    return view


def is_booking_open(year):
    """
    When passed a given year, returns True if booking is open.
    """
    return Price.objects.filter(year=year).count() == len(VALUED_PRICE_TYPES) and Camp.objects.filter(year=year).exists()

is_booking_open_thisyear = lambda: is_booking_open(get_thisyear())


# Views

class BookingIndex(DefaultMetaData, TemplateView):
    metadata_title = "Booking"
    template_name = "cciw/bookings/index.html"

    def get(self, request):
        year = get_thisyear()
        bookingform_relpath = "%s/booking_form_%s.pdf" % (settings.BOOKINGFORMDIR, year)
        if os.path.isfile("%s/%s" % (settings.MEDIA_ROOT, bookingform_relpath)):
            self.context['bookingform'] = bookingform_relpath
        prices = list(Price.objects.filter(year=year))
        booking_open = is_booking_open(year)
        self.context['booking_open'] = booking_open
        if booking_open:
            self.context['price_full'] = [p for p in prices if p.price_type == PRICE_FULL][0].price
            self.context['price_2nd_child'] = [p for p in prices if p.price_type == PRICE_2ND_CHILD][0].price
            self.context['price_3rd_child'] = [p for p in prices if p.price_type == PRICE_3RD_CHILD][0].price
        return super(BookingIndex, self).get(request)


def next_step(account):
    if account.has_account_details():
        return HttpResponseRedirect(reverse('cciw.bookings.views.add_place'))
    else:
        return HttpResponseRedirect(reverse('cciw.bookings.views.account_details'))

class BookingStart(DefaultMetaData, FormMixin, TemplateResponseMixin, ProcessFormView):
    metadata_title = "Booking email address"
    form_class = EmailForm
    template_name = 'cciw/bookings/start.html'
    success_url = reverse_lazy('cciw.bookings.views.email_sent')
    extra_context = {'booking_open': is_booking_open_thisyear}

    def dispatch(self, request, *args, **kwargs):
        account = get_booking_account_from_cookie(request)
        if account is not None:
            return next_step(account)
        return super(BookingStart, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        account, new = BookingAccount.objects.get_or_create(email=form.cleaned_data['email'])
        send_verify_email(self.request, account)
        return super(BookingStart, self).form_valid(form)


class BookingEmailSent(DefaultMetaData, TemplateView):
    metadata_title = "Booking email address"
    template_name = "cciw/bookings/email_sent.html"


def verify_email(request, account_id, token):
    fail = lambda: HttpResponseRedirect(reverse('cciw.bookings.views.verify_email_failed'))
    try:
        account = BookingAccount.objects.get(id=account_id)
    except BookingAccount.DoesNotExist:
        return fail()

    if check_email_verification_token(account, token):
        resp = next_step(account)
        set_booking_account_cookie(resp, account)
        return resp
    else:
        return fail()


class BookingVerifyEmailFailed(DefaultMetaData, TemplateView):
    metadata_title = "Booking account email verification failed"
    template_name = "cciw/bookings/email_verification_failed.html"


class BookingNotLoggedIn(DefaultMetaData, TemplateView):
    metadata_title = "Booking - not logged in"
    template_name = "cciw/bookings/not_logged_in.html"


class BookingAccountDetails(DefaultMetaData, TemplateResponseMixin, BaseUpdateView):
    metadata_title = "Booking account details"
    form_class = AccountDetailsForm
    template_name = 'cciw/bookings/account_details.html'
    success_url = reverse_lazy('cciw.bookings.views.add_place')

    def get_object(self):
        return self.request.booking_account


# MRO problem for BookingAddPlace: we need BaseCreateView.post to come first in
# MRO, to provide self.object = None, then AjaxyFormMixin must be called before
# ProcessFormView, so that for AJAX right thing happens. So we need to hack the
# MRO using a metaclass.

class AjaxMroFixer(type):

    def mro(cls):
        classes = type.mro(cls)
        # Move AjaxyFormMixin to one before last that has a 'post' defined.
        new_list = [c for c in classes if c is not AjaxyFormMixin]
        have_post = [c for c in new_list if 'post' in c.__dict__]
        last = have_post[-1]
        new_list.insert(new_list.index(last), AjaxyFormMixin)
        return new_list

class BookingEditAddBase(DefaultMetaData, TemplateResponseMixin, AjaxyFormMixin):
    template_name = 'cciw/bookings/add_place.html'
    success_url = reverse_lazy('cciw.bookings.views.list_bookings')
    extra_context = {'booking_open': is_booking_open_thisyear,
                     'south_wales_surcharge': lambda: Price.objects.get(year=get_thisyear(),
                                                                        price_type=PRICE_SOUTH_WALES_TRANSPORT).price}

    def post(self, request, *args, **kwargs):
        if not is_booking_open_thisyear():
            # Redirect to same view, but GET
            return HttpResponseRedirect(request.get_full_path())
        else:
            return super(BookingEditAddBase, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.account = self.request.booking_account
        form.instance.agreement_date = datetime.now()
        form.instance.auto_set_amount_due()
        form.instance.state = BOOKING_INFO_COMPLETE
        messages.info(self.request, 'Details for "%s" were saved successfully' % form.instance.name)
        return super(BookingEditAddBase, self).form_valid(form)


class BookingAddPlace(BookingEditAddBase, BaseCreateView):
    __metaclass__ = AjaxMroFixer
    metadata_title = "Booking - add place"
    form_class = AddPlaceForm


class BookingEditPlace(BookingEditAddBase, BaseUpdateView):
    __metaclass__ = AjaxMroFixer
    metadata_title = "Booking - edit place"
    form_class = AddPlaceForm

    def post(self, request, *args, **kwargs):
        if not self.get_object().is_user_editable():
            # just do a redirect to same view, which will display
            # the message about read only
            return HttpResponseRedirect(request.get_full_path())
        else:
            return super(BookingEditPlace, self).post(request, *args, **kwargs)

    def get_object(self):
        try:
            return self.request.booking_account.bookings.get(id=int(self.kwargs['id']))
        except (ValueError, Booking.DoesNotExist):
            raise Http404

    def get_context_data(self, **kwargs):
        c = super(BookingEditPlace, self).get_context_data(**kwargs)
        if not self.object.is_user_editable():
            c['read_only'] = True
        return c


BOOKING_PLACE_PUBLIC_ATTRS = [
    'id',
    'name',
    'sex',
    'date_of_birth',
    'address',
    'post_code',
    'phone_number',
    'church',
    'south_wales_transport',
    'contact_name',
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

@booking_account_required
@json_response
def places_json(request):
    retval = {'status': 'success'}
    retval['places'] = [dict((k, getattr(b, k)) for k in BOOKING_PLACE_PUBLIC_ATTRS)
                        for b in request.booking_account.bookings.all()]
    return retval


class BookingListBookings(DefaultMetaData, TemplateView):
    metadata_title = "Booking - checkout"
    template_name = "cciw/bookings/list_bookings.html"

    def get_context_data(self, **kwargs):
        c = super(BookingListBookings, self).get_context_data(**kwargs)
        bookings = self.request.booking_account.bookings
        basket_bookings = list(bookings.ready_to_book(get_thisyear()))
        shelf_bookings = list(bookings.ready_to_book(get_thisyear(), shelved=True))
        # Now apply business rules and other custom processing
        total = Decimal('0.00')
        all_bookable = True
        all_unbookable = True
        for l in basket_bookings, shelf_bookings:
            for b in l:
                # decorate object with some attributes to make it easier in template
                b.booking_problems = b.get_booking_problems()
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

        c['basket_bookings'] = basket_bookings
        c['shelf_bookings'] = shelf_bookings
        c['all_bookable'] = all_bookable
        c['all_unbookable'] = all_unbookable
        c['total'] = total
        return c

    def post(self, request, *args, **kwargs):
        if 'add_another' in request.POST:
            return HttpResponseRedirect(reverse('cciw.bookings.views.add_place'))

        bookings = request.booking_account.bookings
        places = (bookings.ready_to_book(get_thisyear(), shelved=True) |
                  bookings.ready_to_book(get_thisyear(), shelved=False))

        def shelve(place):
            place.shelved = True
            place.save()
            messages.info(self.request, 'Place for "%s" moved to shelf' % place.name)

        def unshelve(place):
            place.shelved = False
            place.save()
            messages.info(self.request, 'Place for "%s" moved to basket' % place.name)

        def delete(place):
            messages.info(self.request, 'Place for "%s" deleted' % place.name)
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
                        place = places.get(id=b_id)
                        retval = action(place)
                        if retval is not None:
                            return retval
                    except (ValueError, Booking.DoesNotExist):
                        pass
        return self.get(request, *args, **kwargs)


index = BookingIndex.as_view()
start = BookingStart.as_view()
email_sent = BookingEmailSent.as_view()
verify_email_failed = BookingVerifyEmailFailed.as_view()
account_details = booking_account_required(BookingAccountDetails.as_view())
not_logged_in = BookingNotLoggedIn.as_view()
add_place = booking_account_required(BookingAddPlace.as_view())
edit_place = booking_account_required(BookingEditPlace.as_view())
list_bookings = booking_account_required(BookingListBookings.as_view())
