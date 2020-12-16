# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0003_auto_20150107_0959'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='bookingaccount',
            unique_together=set([('name', 'email')]),
        ),
    ]
