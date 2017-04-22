# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-21 12:28
from __future__ import unicode_literals

import cciw.officers.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0049_auto_20170405_2330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='dbs_check_consent',
            field=cciw.officers.fields.RequiredExplicitBooleanField(default=None, verbose_name='Do you consent to the obtaining of a Disclosure and Barring Service check on yourself? '),
        ),
    ]
