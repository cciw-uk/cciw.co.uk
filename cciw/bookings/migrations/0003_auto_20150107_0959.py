# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def populate_created_online(apps, schema_editor):
    import django
    from django.contrib.admin.models import ADDITION
    from django.contrib.admin.options import get_content_type_for_model
    if django.VERSION >= (1, 8):
        # This migration is broken in 1.8. However, it's not needed any more
        # and only runs in tests, so just disable it.
        return

    Booking = apps.get_model("bookings", "Booking")
    LogEntry = apps.get_model("admin", "LogEntry")
    added_via_admin = [int(l.object_id) for l in LogEntry.objects.filter(content_type=get_content_type_for_model(Booking), action_flag=ADDITION)]

    Booking.objects.update(created_online=True)
    Booking.objects.filter(id__in=added_via_admin).update(created_online=False)


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_booking_created_online'),
        ('admin', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            populate_created_online
        )
    ]
