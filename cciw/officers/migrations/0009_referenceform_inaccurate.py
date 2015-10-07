# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0008_referenceaction_inaccurate'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenceform',
            name='inaccurate',
            field=models.BooleanField(default=False),
        ),
    ]
