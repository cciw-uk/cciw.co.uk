# Generated by Django 3.1.7 on 2021-05-28 16:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0042_customagreement"),
    ]

    operations = [
        migrations.RenameField(
            model_name="customagreement",
            old_name="text",
            new_name="text_html",
        ),
    ]