# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0006_campname'),
    ]

    operations = [
        migrations.AddField(
            model_name='camp',
            name='camp_name',
            field=models.ForeignKey(null=True, related_name='camps', to='cciwmain.CampName', on_delete=models.CASCADE),
        ),
    ]
