from django.contrib import admin
from django.urls.base import reverse
from django.utils.html import format_html
from paypal.standard.ipn.admin import PayPalIPNAdmin
from paypal.standard.ipn.models import PayPalIPN

from cciw.bookings.models import parse_paypal_custom_field


def account(ipn_obj: PayPalIPN):
    account = parse_paypal_custom_field(ipn_obj.custom)
    if account is not None:
        return format_html(
            '<a href="{0}">{1}</a>', reverse("admin:bookings_bookingaccount_change", args=[account.id]), account.name
        )


class MyPayPalIPNAdmin(PayPalIPNAdmin):
    list_filter = list(PayPalIPNAdmin.list_filter) + ["item_name"]

    list_display = [
        "txn_id",
        account,
        "mc_gross",
        "item_name",
        "payment_status",
        "flag",
        "created_at",
    ]


admin.site.unregister(PayPalIPN)
admin.site.register(PayPalIPN, MyPayPalIPNAdmin)
