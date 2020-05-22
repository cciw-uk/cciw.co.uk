# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def forwards(apps, schema):
    Application = apps.get_model('officers', 'Application')
    Referee = apps.get_model('officers', 'Referee')

    for app in Application.objects.all():
        for i in [1, 2]:
            Referee.objects.create(
                application=app,
                referee_number=i,
                name=getattr(app, f'referee{i}_name'),
                address=getattr(app, f'referee{i}_address'),
                tel=getattr(app, f'referee{i}_tel'),
                mobile=getattr(app, f'referee{i}_mobile'),
                email=getattr(app, f'referee{i}_email'),
            )


def backwards(apps, schema):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0011_referee'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
