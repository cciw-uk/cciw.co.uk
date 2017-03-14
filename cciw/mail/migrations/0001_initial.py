# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-12 18:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import jsonfield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('event', models.CharField(max_length=50)),
                ('data', jsonfield.fields.JSONField()),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]