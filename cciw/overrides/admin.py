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
    list_filter = [
        "item_name",
        "payment_status",
        "flag",
        "txn_type",
    ]

    list_display = [
        "txn_id",
        account,
        "mc_gross",
        "item_name",
        "payment_status",
        "flag",
        "created_at",
    ]
    fieldsets = (
        (
            None,
            {
                "fields": [
                    "flag",
                    "txn_id",
                    "txn_type",
                    "payment_status",
                    "payment_date",
                    "transaction_entity",
                    "reason_code",
                    "pending_reason",
                    "mc_currency",
                    "mc_gross",
                    "mc_fee",
                    "mc_handling",
                    "mc_shipping",
                    "auth_status",
                    "auth_amount",
                    "auth_exp",
                    "auth_id",
                ]
            },
        ),
        (
            "Buyer/donator",
            {
                "description": "The information about the Buyer.",
                "fields": [
                    "first_name",
                    "last_name",
                    "payer_business_name",
                    "payer_email",
                    "payer_id",
                    "payer_status",
                    "contact_phone",
                    "residence_country",
                ],
            },
        ),
        (
            "Address",
            {
                "description": "The address of the Buyer.",
                "classes": ("collapse",),
                "fields": [
                    "address_city",
                    "address_country",
                    "address_country_code",
                    "address_name",
                    "address_state",
                    "address_status",
                    "address_street",
                    "address_zip",
                ],
            },
        ),
        (
            "Seller",
            {
                "description": "The information about the Seller.",
                "classes": ("collapse",),
                "fields": [
                    "business",
                    "item_name",
                    "item_number",
                    "quantity",
                    "receiver_email",
                    "receiver_id",
                    "custom",
                    "invoice",
                    "memo",
                ],
            },
        ),
        (
            "Recurring",
            {
                "description": "Information about recurring Payments.",
                "classes": ("collapse",),
                "fields": [
                    "profile_status",
                    "initial_payment_amount",
                    "amount_per_cycle",
                    "outstanding_balance",
                    "period_type",
                    "product_name",
                    "product_type",
                    "recurring_payment_id",
                    "receipt_id",
                    "next_payment_date",
                ],
            },
        ),
        (
            "Subscription",
            {
                "description": "Information about recurring Subscptions.",
                "classes": ("collapse",),
                "fields": [
                    "subscr_date",
                    "subscr_effective",
                    "period1",
                    "period2",
                    "period3",
                    "amount1",
                    "amount2",
                    "amount3",
                    "mc_amount1",
                    "mc_amount2",
                    "mc_amount3",
                    "recurring",
                    "reattempt",
                    "retry_at",
                    "recur_times",
                    "username",
                    "password",
                    "subscr_id",
                ],
            },
        ),
        (
            "Admin",
            {
                "description": "Additional Info.",
                "classes": ("collapse",),
                "fields": [
                    "test_ipn",
                    "ipaddress",
                    "query",
                    "response",
                    "flag_code",
                    "flag_info",
                ],
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        return super().get_fieldsets(request, obj)


admin.site.unregister(PayPalIPN)
admin.site.register(PayPalIPN, MyPayPalIPNAdmin)
