# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0014_auto_20151007_1555'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referenceaction',
            name='referee',
            field=models.ForeignKey(to='officers.Referee', related_name='actions', on_delete=models.CASCADE),
        ),
    ]
