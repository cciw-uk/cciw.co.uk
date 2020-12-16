# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0004_auto_20150729_1055'),
    ]

    operations = [
        migrations.AddField(
            model_name='camp',
            name='last_booking_date',
            field=models.DateField(null=True, blank=True, help_text='Camp start date will be used if left empty.'),
        ),
    ]
