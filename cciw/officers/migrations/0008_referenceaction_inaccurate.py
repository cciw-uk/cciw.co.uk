# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0007_auto_20150814_1110'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenceaction',
            name='inaccurate',
            field=models.BooleanField(default=False),
        ),
    ]
