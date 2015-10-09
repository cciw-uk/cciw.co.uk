# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0021_auto_20151007_1632'),
    ]

    operations = [
        migrations.RenameModel('ReferenceForm', 'Reference')
    ]
