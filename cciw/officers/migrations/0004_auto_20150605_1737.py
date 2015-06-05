# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import cciw.officers.fields


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0003_auto_20150423_2007'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='crbapplication',
            options={'verbose_name_plural': 'CRB/DBS Disclosures', 'verbose_name': 'CRB/DBS Disclosure'},
        ),
        migrations.AlterModelOptions(
            name='crbformlog',
            options={'verbose_name_plural': 'CRB/DBS form logs', 'verbose_name': 'CRB/DBS form log'},
        ),
        migrations.AlterModelOptions(
            name='referenceaction',
            options={'ordering': ['created']},
        ),
        migrations.AlterField(
            model_name='application',
            name='address_email',
            field=cciw.officers.fields.RequiredEmailField(max_length=254, verbose_name='e-mail', blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='allegation_declaration',
            field=cciw.officers.fields.RequiredExplicitBooleanField(default=None, verbose_name='To your knowledge have you ever had any allegation made against you concerning children/young people which has been reported to and investigated by Social Services and /or the Police?'),
        ),
        migrations.AlterField(
            model_name='application',
            name='concern_declaration',
            field=cciw.officers.fields.RequiredExplicitBooleanField(default=None, verbose_name='Has there ever been any cause for concern regarding your conduct with children/young people?'),
        ),
        migrations.AlterField(
            model_name='application',
            name='crb_check_consent',
            field=cciw.officers.fields.RequiredExplicitBooleanField(default=None, verbose_name='Do you consent to the obtaining of a Disclosure and Barring Service check on yourself? '),
        ),
        migrations.AlterField(
            model_name='application',
            name='crime_declaration',
            field=cciw.officers.fields.RequiredExplicitBooleanField(default=None, verbose_name='Have you ever been charged with or convicted of a criminal offence or are the subject of criminal proceedings?'),
        ),
        migrations.AlterField(
            model_name='application',
            name='officer',
            field=models.ForeignKey(related_name='applications', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='referee1_email',
            field=models.EmailField(max_length=254, verbose_name='e-mail', blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='referee2_email',
            field=models.EmailField(max_length=254, verbose_name='e-mail', blank=True),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='camp',
            field=models.ForeignKey(related_name='invitations', to='cciwmain.Camp'),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='officer',
            field=models.ForeignKey(related_name='invitations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='referenceaction',
            name='action_type',
            field=models.CharField(max_length=20, choices=[('requested', 'Reference requested'), ('received', 'Reference receieved'), ('nag', 'Applicant nagged')]),
        ),
        migrations.AlterField(
            model_name='referenceform',
            name='concerns',
            field=models.TextField(verbose_name="Have you ever had concerns about either this applicant's ability or suitability to work with children and young people?"),
        ),
    ]
