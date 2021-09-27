from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cciwmain", "0015_auto_20151201_1215"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="camp",
            name="previous_camp",
        ),
    ]
