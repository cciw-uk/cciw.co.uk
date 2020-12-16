# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0019_auto_20151007_1611'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='reference',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='reference',
            name='application',
        ),
        migrations.AlterModelOptions(
            name='referee',
            options={'ordering': ('application__date_submitted', 'application__officer__first_name', 'application__officer__last_name', 'referee_number')},
        ),
        migrations.DeleteModel(
            name='Reference',
        ),
    ]
