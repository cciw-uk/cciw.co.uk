class DebugMiddleware(object):
    def process_response(self, request, response):
        from cciw.bookings.models import BookingAccount
        from cciw.bookings.views import set_booking_account_cookie

        if 'booking_account' in request.GET:
            set_booking_account_cookie(response, BookingAccount.objects.get(email=request.GET['booking_account']))

        return response

    def process_request(self, request):

        if 'as' in request.GET:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.get(username=request.GET['as'])
            request.session['_auth_user_id'] = user.id
            request.session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
            request.user = user
            request.session.save()
