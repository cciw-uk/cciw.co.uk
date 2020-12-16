# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-06 22:14
from __future__ import unicode_literals

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0010_auto_20151210_1900'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountTransferPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('from_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_from_payments', to='bookings.BookingAccount')),
                ('to_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_to_payments', to='bookings.BookingAccount')),
            ],
        ),
        migrations.AlterField(
            model_name='payment',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='bookings.BookingAccount'),
        ),
    ]
