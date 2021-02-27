# Generated by Django 3.1.5 on 2021-02-04 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0033_auto_20190801_2018'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingaccount',
            name='subscribe_to_mailings',
            field=models.BooleanField(blank=True, default=None, null=True, verbose_name='Receive mailings about future camps'),
        ),
    ]