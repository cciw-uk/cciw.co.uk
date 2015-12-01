# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0012_auto_20151201_1154'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camp',
            name='number',
        ),
    ]
