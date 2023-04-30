from django.apps import AppConfig


class BookingsConfig(AppConfig):
    name = "cciw.bookings"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.contrib import admin
        from paypal.standard.ipn.models import PayPalIPN

        # Customize some other admins:
        PayPalIPNAdmin = admin.site._registry[PayPalIPN]
        if "item_name" not in PayPalIPNAdmin.list_filter:
            PayPalIPNAdmin.list_filter = list(PayPalIPNAdmin.list_filter) + ["item_name"]
