# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0017_auto_20151007_1604'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referenceform',
            name='referee',
            field=models.OneToOneField(to='officers.Referee'),
        ),
    ]
