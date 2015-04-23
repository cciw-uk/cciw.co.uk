# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from datetime import datetime

from django.db import models, migrations
from django.utils import timezone


def create_reference_actions(apps, schema_editor):
    Reference = apps.get_model("officers", "Reference")
    ReferenceAction = apps.get_model("officers", "ReferenceAction")
    User = apps.get_model("auth", "User")

    for r in Reference.objects.all():
        if r.comments.strip() == "":
            continue

        for l in r.comments.split("\n"):
            m = re.match("Reference requested by user ([^ ]*).* on (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", l)
            if m is not None:
                dt = timezone.utc.localize(datetime.strptime(m.groups()[1], "%Y-%m-%d %H:%M:%S"))
                username = m.groups()[0]
                user = User.objects.get(username=username)
                ReferenceAction.objects.create(action_type="requested",
                                               created=dt,
                                               reference=r,
                                               user=user)

            m = re.match("Reference received via online system on (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", l)
            if m is not None:
                dt = timezone.utc.localize(datetime.strptime(m.groups()[0], "%Y-%m-%d %H:%M:%S"))
                ReferenceAction.objects.create(action_type="received",
                                               created=dt,
                                               reference=r,
                                               user=None)


def remove(apps, schema_editor):
    ReferenceAction = apps.get_model("officers", "ReferenceAction")
    ReferenceAction.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0002_referenceaction'),
    ]

    operations = [
        migrations.RunPython(create_reference_actions, remove),
    ]
