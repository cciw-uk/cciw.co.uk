from django.db import migrations, models

import cciw.officers.fields


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0010_auto_20151007_1420'),
    ]

    operations = [
        migrations.CreateModel(
            name='Referee',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('referee_number', models.SmallIntegerField(verbose_name='Referee number', choices=[(1, '1'), (2, '2')])),
                ('name', cciw.officers.fields.RequiredCharField(max_length=100, blank=True, help_text='Name only - please do not include job title or other information.', verbose_name="First referee's name")),
                ('address', cciw.officers.fields.RequiredAddressField(blank=True, help_text='Full address, including post code and country', verbose_name='address')),
                ('tel', models.CharField(max_length=22, blank=True, verbose_name='telephone')),
                ('mobile', models.CharField(max_length=22, blank=True, verbose_name='mobile')),
                ('email', models.EmailField(max_length=254, blank=True, verbose_name='e-mail')),
                ('application', models.ForeignKey(to='officers.Application', on_delete=models.CASCADE)),
            ],
        ),
    ]
