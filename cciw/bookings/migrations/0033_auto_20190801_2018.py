# Generated by Django 2.1.11 on 2019-08-01 19:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0032_auto_20181215_1205'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='can_swim_25m',
            field=models.BooleanField(blank=True, default=False, verbose_name='Can the camper swim 25m?'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='created_online',
            field=models.BooleanField(blank=True, default=False),
        ),
        migrations.AlterField(
            model_name='booking',
            name='serious_illness',
            field=models.BooleanField(blank=True, default=False),
        ),
        migrations.AlterField(
            model_name='booking',
            name='south_wales_transport',
            field=models.BooleanField(blank=True, default=False, verbose_name='require transport from South Wales'),
        ),
        migrations.AlterField(
            model_name='bookingaccount',
            name='email_communication',
            field=models.BooleanField(blank=True, default=True, verbose_name='Receive all communication from CCiW by email where possible'),
        ),
        migrations.AlterField(
            model_name='bookingaccount',
            name='share_phone_number',
            field=models.BooleanField(blank=True, default=False, verbose_name='Allow this phone number to be passed on to other parents to help organise transport'),
        ),
    ]
