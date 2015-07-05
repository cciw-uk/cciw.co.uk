# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0004_auto_20150605_1737'),
    ]

    operations = [
        migrations.AddField(
            model_name='crbapplication',
            name='other_organisation',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AddField(
            model_name='crbapplication',
            name='registered_with_dbs_update',
            field=models.NullBooleanField(verbose_name='registered with DBS update service'),
        ),
        migrations.AddField(
            model_name='crbapplication',
            name='requested_by',
            field=models.CharField(choices=[('CCIW', 'CCIW'), ('other', 'Other'), ('unknown', 'Unknown')], max_length=20, default='unknown'),
        ),
    ]