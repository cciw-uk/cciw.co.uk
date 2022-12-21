# Generated by Django 4.0.7 on 2022-11-23 18:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0004_alter_camprole_name"),
    ]

    operations = [
        migrations.RunSQL(
            """
            INSERT INTO officers_camprole (name) VALUES
               ('Leader'),
               ('Assistant Leader'),
               ('Chaplain'),
               ('Tent Officer'),
               ('Junior Tent Officer'),
               ('Lead Kitchen'),
               ('Kitchen Helper'),
               ('Site maintenance')

              ON CONFLICT DO NOTHING;

            """,
            "",
            elidable=True,
        ),
    ]