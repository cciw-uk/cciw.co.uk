# Generated by Django 3.2.6 on 2021-10-11 18:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0065_reference_given_in_confidence"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="reference",
            options={"base_manager_name": "objects", "verbose_name": "reference"},
        ),
    ]