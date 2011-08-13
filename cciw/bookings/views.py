# == Booking process ==

# = Primary route =
# Step 0 /booking/
#  - shows overview of options, including
#    - get brochure through post
#    - print booking m=form yourself
#    - book online

# Step 1  /booking/start/
#  - enter email address
#    - must be contact address for person booking
#      "You may want to add 'bookings@cciw.co.uk' to your known contacts list to
#      ensure our email is not treated as spam"

#  - On POST
#    - if verfied email already in signed cookie then:
#      - if BookingAccount.name already set skip to step 4
#      - otherwise skip to step 3
#
#  - send email verification email
#    - has a link to step 2
#
#  - inform about checking email

# Step 2 /booking/v/
#  - if new account, create in DB
#  - set signed cookie with timestamp, lasting x weeks
#  - redirect to step 3

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

import os

from django.conf import settings
from django.views.generic.base import TemplateView, TemplateResponseMixin
from django.views.generic.edit import ProcessFormView, FormMixin

from cciw.cciwmain.common import get_thisyear, DefaultMetaData

from cciw.bookings.forms import EmailForm

class BookingIndex(DefaultMetaData, TemplateView):
    metadata_title = "Booking"
    template_name = "cciw/bookings/index.html"

    def get(self, request):
        year = get_thisyear()
        bookingform_relpath = "%s/booking_form_%s.pdf" % (settings.BOOKINGFORMDIR, year)
        if os.path.isfile("%s/%s" % (settings.MEDIA_ROOT, bookingform_relpath)):
            self.context['bookingform'] = bookingform_relpath
        return super(BookingIndex, self).get(request)


class BookingStart(DefaultMetaData, FormMixin, TemplateResponseMixin, ProcessFormView):
    metadata_title = "Booking account details"
    form_class = EmailForm
    template_name = 'cciw/bookings/start.html'



index = BookingIndex.as_view()
start = BookingStart.as_view()
