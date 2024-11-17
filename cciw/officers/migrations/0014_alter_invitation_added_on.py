# Generated by Django 4.2.5 on 2024-03-30 21:13

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("officers", "0013_rename_date_added_invitation_added_on"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invitation",
            name="added_on",
            field=models.DateField(default=datetime.date.today, verbose_name="date added"),
        ),
    ]