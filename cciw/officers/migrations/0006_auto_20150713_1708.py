# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0005_auto_20150605_1738'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='full_maiden_name',
            field=models.CharField(max_length=100, help_text='Name before getting married.', blank=True, verbose_name='full maiden name'),
        ),
        migrations.AlterField(
            model_name='crbapplication',
            name='officer',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='crb_applications'),
        ),
        migrations.AlterField(
            model_name='crbapplication',
            name='requested_by',
            field=models.CharField(max_length=20, default='unknown', choices=[('CCIW', 'CCIW'), ('other', 'Other organisation'), ('unknown', 'Unknown')]),
        ),
    ]
