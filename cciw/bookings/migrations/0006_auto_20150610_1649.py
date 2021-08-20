# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import pytz
from django.db import migrations
from django.utils import timezone

PAYPAL_DATE_FORMATS = [
    "%H:%M:%S %b. %d, %Y PST",
    "%H:%M:%S %b. %d, %Y PDT",
    "%H:%M:%S %b %d, %Y PST",
    "%H:%M:%S %b %d, %Y PDT",
]


def parse_date(datestring):
    for format in PAYPAL_DATE_FORMATS:
        try:
            return datetime.strptime(datestring, format)
        except (ValueError, TypeError):
            continue


def fix_ipn_dates(apps, schema_editor):
    PayPalIPN = apps.get_model("ipn", "PayPalIPN")

    for ipn in PayPalIPN.objects.all():
        # Need to recreate PayPalIPN.posted_data_dict
        posted_data_dict = None
        if ipn.query:
            from django.http import QueryDict
            roughdecode = dict(item.split('=', 1) for item in ipn.query.split('&'))
            encoding = roughdecode.get('charset')
            if encoding is not None:
                query = ipn.query.encode('ascii')
                data = QueryDict(query, encoding=encoding)
                posted_data_dict = data.dict()
        if posted_data_dict is None:
            continue

        for field in ['time_created', 'payment_date', 'next_payment_date', 'subscr_date', 'subscr_effective']:
            if field in posted_data_dict:
                raw = posted_data_dict[field]
                naive = parse_date(raw)
                if naive is not None:
                    aware = timezone.make_aware(naive, pytz.timezone('US/Pacific'))
                    setattr(ipn, field, aware)
        ipn.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0005_auto_20150407_1333'),
        ('ipn', '0003_auto_20141117_1647'),
    ]

    operations = [
        migrations.RunPython(fix_ipn_dates,
                             lambda apps, schema_editor: None)  # allowing reverse migration is harmless)
    ]
