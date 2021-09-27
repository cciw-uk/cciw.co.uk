import colorful.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cciwmain", "0017_auto_20151201_1238"),
    ]

    operations = [
        migrations.AddField(
            model_name="campname",
            name="color",
            field=colorful.fields.RGBColorField(default="#ffffff"),
            preserve_default=False,
        ),
    ]
