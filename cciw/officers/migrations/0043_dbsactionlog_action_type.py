# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-04 11:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0042_dbsactionlog_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='dbsactionlog',
            name='action_type',
            field=models.CharField(choices=[('form_sent', 'DBS form sent'), ('leader_alert_sent', 'Alert sent to leader')], default='form_sent', max_length=20, verbose_name='action type'),
        ),
    ]
