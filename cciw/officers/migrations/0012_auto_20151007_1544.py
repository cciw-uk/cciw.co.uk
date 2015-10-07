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
                name=getattr(app, 'referee{0}_name'.format(i)),
                address=getattr(app, 'referee{0}_address'.format(i)),
                tel=getattr(app, 'referee{0}_tel'.format(i)),
                mobile=getattr(app, 'referee{0}_mobile'.format(i)),
                email=getattr(app, 'referee{0}_email'.format(i)),
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
