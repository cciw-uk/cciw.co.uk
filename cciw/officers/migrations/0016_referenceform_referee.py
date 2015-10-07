# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0015_auto_20151007_1603'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenceform',
            name='referee',
            field=models.OneToOneField(null=True, to='officers.Referee'),
        ),
    ]
