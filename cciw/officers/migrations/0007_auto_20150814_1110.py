# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0006_auto_20150713_1708'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referenceaction',
            name='action_type',
            field=models.CharField(max_length=20, choices=[('requested', 'Reference requested'), ('received', 'Reference received'), ('filledin', 'Reference filled in manually'), ('nag', 'Applicant nagged')]),
        ),
    ]
