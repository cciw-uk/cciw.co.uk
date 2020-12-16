# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Camp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveSmallIntegerField(verbose_name='year')),
                ('number', models.PositiveSmallIntegerField(verbose_name='number')),
                ('minimum_age', models.PositiveSmallIntegerField()),
                ('maximum_age', models.PositiveSmallIntegerField()),
                ('start_date', models.DateField(verbose_name='start date')),
                ('end_date', models.DateField(verbose_name='end date')),
                ('max_campers', models.PositiveSmallIntegerField(verbose_name='maximum campers', default=80)),
                ('max_male_campers', models.PositiveSmallIntegerField(verbose_name='maximum male campers', default=60)),
                ('max_female_campers', models.PositiveSmallIntegerField(verbose_name='maximum female campers', default=60)),
                ('south_wales_transport_available', models.BooleanField(verbose_name='South Wales transport available (pre 2015 only)', default=False)),
                ('online_applications', models.BooleanField(verbose_name='Accepts online applications from officers.', default=True)),
                ('admins', models.ManyToManyField(blank=True, help_text='These users can manage references/applications for the camp. Not for normal officers.', to=settings.AUTH_USER_MODEL, verbose_name='admins', related_name='camps_as_admin')),
            ],
            options={
                'ordering': ['-year', 'number'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(verbose_name='Name', max_length=40)),
                ('info', models.TextField(blank=True, verbose_name='Information (Plain text)')),
                ('users', models.ManyToManyField(blank=True, verbose_name='Associated admin users', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'people',
                'ordering': ('name',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short_name', models.CharField(verbose_name='Short name', unique=True, max_length=25)),
                ('slug_name', models.SlugField(max_length=25, blank=True, verbose_name='Machine name', unique=True)),
                ('long_name', models.CharField(verbose_name='Long name', max_length=50)),
                ('info', models.TextField(verbose_name='Description (HTML)')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='camp',
            name='chaplain',
            field=models.ForeignKey(null=True, to='cciwmain.Person', blank=True, verbose_name='chaplain', related_name='camps_as_chaplain', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='camp',
            name='leaders',
            field=models.ManyToManyField(blank=True, verbose_name='leaders', to='cciwmain.Person', related_name='camps_as_leader'),
            preserve_default=True,
        ),
    ]
