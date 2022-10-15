import re

from django.db import migrations

BAD_EMPTY_VALS = [
    "n/a",
    "not applicable",
    "none",
    "no",
    "no diet",
    "na",
    "nil",
    "no allergies",
    "n0",
    "none known",
    "no known allergies",
    "non",
    "none that i know of",
    "no medication",
    "no known difficulties",
]

FIELDS = [
    "dietary_requirements",
    "church",
    "allergies",
    "regular_medication_required",
    "illnesses",
    "learning_difficulties",
]


def fix_empty_values(apps, schema_editor):
    Booking = apps.get_model("bookings", "Booking")

    for booking in Booking.objects.all():
        dirty = False
        for field in FIELDS:
            val = getattr(booking, field)
            norm_val = re.sub(r"[\/\\\.\-]*$", "", val.strip()).lower()
            if (norm_val in BAD_EMPTY_VALS) or (norm_val == "" and val != ""):
                print(f"Booking: {booking.id} - discarding {field} value {repr(val)}")
                setattr(booking, field, "")
                dirty = True
        if dirty:
            print(f"Saving booking {booking.id}")
            booking.save()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0006_auto_20150610_1649"),
    ]

    operations = [
        migrations.RunPython(
            fix_empty_values, lambda apps, schema_editor: None, elidable=True
        )  # allowing reverse migration is harmless)
    ]
