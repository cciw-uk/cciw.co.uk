from django.contrib.auth import login


def debug_middleware(get_response):
    def middleware(request):
        from cciw.bookings.models import BookingAccount
        from cciw.bookings.middleware import set_booking_account_cookie

        if 'as' in request.GET:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(username=request.GET['as'])
            user.backend = 'cciw.auth.CciwAuthBackend'  # fake a call to authenticate
            login(request, user)

        response = get_response(request)

        if 'booking_account' in request.GET:
            set_booking_account_cookie(response, BookingAccount.objects.get(email=request.GET['booking_account']))

        return response

    return middleware
