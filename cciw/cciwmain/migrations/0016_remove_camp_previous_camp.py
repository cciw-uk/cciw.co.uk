# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0015_auto_20151201_1215'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camp',
            name='previous_camp',
        ),
    ]
