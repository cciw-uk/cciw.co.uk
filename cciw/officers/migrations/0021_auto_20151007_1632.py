# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0020_auto_20151007_1631'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='referee',
            unique_together=set([('application', 'referee_number')]),
        ),
    ]
