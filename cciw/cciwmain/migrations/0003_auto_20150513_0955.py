# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0002_auto_20141231_1034'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255, help_text='Internal name of role, should remain fixed once created', verbose_name='Name')),
                ('description', models.CharField(max_length=255, help_text='Public name/title of role', verbose_name='Title')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='person',
            name='phone_number',
            field=models.CharField(max_length=40, help_text='Required only for staff like CPO who need to be contacted.', blank=True, verbose_name='Phone number'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='roles',
            field=models.ManyToManyField(blank=True, to='cciwmain.Role'),
            preserve_default=True,
        ),
    ]
