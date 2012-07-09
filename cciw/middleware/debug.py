class DebugMiddleware(object):
    def process_response(self, request, response):
        from cciw.bookings.models import BookingAccount
        from cciw.bookings.views import set_booking_account_cookie

        if 'booking_account' in request.GET:
            set_booking_account_cookie(response, BookingAccount.objects.get(email=request.GET['booking_account']))

        return response
