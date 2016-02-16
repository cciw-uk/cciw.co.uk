# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-15 20:52
from __future__ import unicode_literals

from django.db import migrations, models
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0016_auto_20160215_1947'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingaccount',
            name='address_city',
            field=models.CharField(blank=True, max_length=255, verbose_name='town/city'),
        ),
        migrations.AddField(
            model_name='bookingaccount',
            name='address_country',
            field=django_countries.fields.CountryField(blank=True, max_length=2, null=True, verbose_name='country'),
        ),
        migrations.AddField(
            model_name='bookingaccount',
            name='address_county',
            field=models.CharField(blank=True, max_length=255, verbose_name='county/state'),
        ),
        migrations.AddField(
            model_name='bookingaccount',
            name='address_line1',
            field=models.CharField(blank=True, max_length=255, verbose_name='address line 1'),
        ),
        migrations.AddField(
            model_name='bookingaccount',
            name='address_line2',
            field=models.CharField(blank=True, max_length=255, verbose_name='address line 2'),
        ),
        migrations.AlterField(
            model_name='bookingaccount',
            name='address_post_code',
            field=models.CharField(blank=True, max_length=10, verbose_name='post code'),
        ),
    ]
