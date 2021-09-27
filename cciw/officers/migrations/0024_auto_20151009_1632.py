from django.db import migrations

import cciw.officers.fields


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0023_auto_20151008_0857"),
    ]

    operations = [
        migrations.AlterField(
            model_name="referee",
            name="name",
            field=cciw.officers.fields.RequiredCharField(
                blank=True,
                verbose_name="Name",
                max_length=100,
                help_text="Name only - please do not include job title or other information.",
            ),
        ),
    ]
