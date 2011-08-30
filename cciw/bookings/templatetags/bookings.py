from django import template
from django.core.urlresolvers import reverse
from django.utils.html import escape

from cciw.bookings.views import ensure_booking_acount_attr

register = template.Library()


@register.simple_tag(takes_context=True)
def bookingbar(context):

    request = context['request']
    ensure_booking_acount_attr(request)
    booking_account = request.booking_account
    logged_in = booking_account is not None
    current_stage = context['stage']
    has_account_details = logged_in and request.booking_account.has_account_details()

    # Tuple of (name, caption, if this a link, url, message if inaccessible):
    msg_need_login = 'Must be logged in to access this'
    msg_need_account_details = 'Need account details to access this' if logged_in else 'Must be logged in to access this'
    stages = [
        ('email',  'Log in', False,
         '',
         'Use the "log out" link if you need to log in as someone else'),

        ('account', 'Account details', logged_in,
         reverse('cciw.bookings.views.account_details'),
         msg_need_login),

        ('place', 'Place details', logged_in and has_account_details,
         reverse('cciw.bookings.views.add_place'),
         msg_need_account_details),

        ('list', 'Checkout', logged_in and has_account_details,
         reverse('cciw.bookings.views.list_bookings'),
         msg_need_account_details),

        ('pay', 'Pay', logged_in and has_account_details,
         reverse('cciw.bookings.views.pay'),
         msg_need_account_details),

        ]

    out = []
    out.append("""
<div id="bookingbar">
  <div id="bookingbartop">""")

    if not logged_in:
        out.append("Not logged in")
    else:
        out.append("Bookings: %s" % escape(request.booking_account.email))
        out.append(' | <a href="%s">Account overview</a>' % 'TODO')
        out.append(' | <a href="%s">Log out</a>' % 'TODO')
    out.append("</div>")

    out.append("<ul>")
    for name, caption, is_link, url, msg in stages:
        if is_link and name != current_stage:
            out.append('<li><a href="%s">%s</a></li>' % (escape(url), escape(caption)))
        elif name == current_stage:
            out.append('<li><span class="active">%s</span></li>' % escape(caption))
        else:
            out.append('<li><span title="%s">%s</span></li>' % (escape(msg), escape(caption)))

    out.append("</ul></div>")
    return ''.join(out)
