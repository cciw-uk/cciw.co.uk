# Generated by Django 4.2.5 on 2024-03-30 20:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0060_rename_date_of_birth_booking_birth_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="birth_date",
            field=models.DateField(verbose_name="date of birth"),
        ),
    ]
