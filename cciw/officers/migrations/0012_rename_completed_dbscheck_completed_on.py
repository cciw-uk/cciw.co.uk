# Generated by Django 4.2.5 on 2024-03-30 21:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("officers", "0011_alter_application_options_alter_referee_options_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dbscheck",
            old_name="completed",
            new_name="completed_on",
        ),
    ]
