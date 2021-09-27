from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0008_referenceaction_inaccurate"),
    ]

    operations = [
        migrations.AddField(
            model_name="referenceform",
            name="inaccurate",
            field=models.BooleanField(default=False),
        ),
    ]
