# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-10 17:28
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0028_auto_20161118_1943'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='booking',
            options={'base_manager_name': 'objects', 'ordering': ['-created']},
        ),
        migrations.AlterModelOptions(
            name='manualpayment',
            options={'base_manager_name': 'objects'},
        ),
        migrations.AlterModelOptions(
            name='payment',
            options={'base_manager_name': 'objects'},
        ),
        migrations.AlterModelOptions(
            name='refundpayment',
            options={'base_manager_name': 'objects'},
        ),
    ]