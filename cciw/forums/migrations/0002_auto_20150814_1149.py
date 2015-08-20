# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forums', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Email address'),
        ),
    ]
