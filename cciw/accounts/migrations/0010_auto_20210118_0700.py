# Generated by Django 3.1.5 on 2021-01-18 07:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_auto_20201222_1217'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='bad_password',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='password_validators_used',
            field=models.TextField(blank=True),
        ),
    ]