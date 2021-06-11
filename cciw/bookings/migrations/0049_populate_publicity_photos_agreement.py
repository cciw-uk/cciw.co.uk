# Generated by Django 3.1.7 on 2021-06-11 08:37

from django.db import migrations


def forwards(apps, schema_editor):
    Booking = apps.get_model('bookings', 'Booking')
    Booking.objects.filter(agreement=True).update(publicity_photos_agreement=True)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0048_booking_publicity_photos_agreement'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
