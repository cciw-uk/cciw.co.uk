# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0012_auto_20151007_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenceaction',
            name='referee',
            field=models.ForeignKey(related_name='actions', to='officers.Referee', null=True, on_delete=models.CASCADE),
        ),
    ]
