# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_auto_20150407_1332'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='bookingaccount',
            unique_together=set([]),
        ),
    ]
