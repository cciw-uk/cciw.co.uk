# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-02 16:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_auto_20150814_1150'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='origin_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='contenttypes.ContentType'),
        ),
    ]
