# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0011_auto_20151201_1145'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='camp',
            unique_together=set([]),
        ),
    ]
