# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0018_auto_20151007_1606'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='referenceaction',
            name='reference',
        ),
        migrations.RemoveField(
            model_name='referenceform',
            name='reference_info',
        ),
    ]
