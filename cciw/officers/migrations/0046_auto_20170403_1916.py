# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-03 18:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0045_auto_20170403_1856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbscheck',
            name='other_organisation',
            field=models.CharField(blank=True, help_text='If previous answer is not CCIW, please fill in', max_length=255),
        ),
        migrations.AlterField(
            model_name='dbscheck',
            name='requested_by',
            field=models.CharField(choices=[('CCIW', 'CCIW'), ('other', 'Other organisation'), ('unknown', 'Unknown')], default='unknown', help_text='The organisation that asked for this DBS to be done, normally CCIW.', max_length=20),
        ),
    ]