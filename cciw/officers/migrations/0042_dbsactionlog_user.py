# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-04 11:43
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('officers', '0041_auto_20170304_1134'),
    ]

    operations = [
        migrations.AddField(
            model_name='dbsactionlog',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dbsactions_performed', to=settings.AUTH_USER_MODEL, verbose_name='User who performed action'),
        ),
    ]
