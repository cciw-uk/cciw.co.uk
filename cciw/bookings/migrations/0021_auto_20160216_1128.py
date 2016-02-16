# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-16 11:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0020_booking_gp_post_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='address_post_code',
            field=models.CharField(max_length=10, verbose_name='post code'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='gp_post_code',
            field=models.CharField(max_length=10, verbose_name='post code'),
        ),
    ]
