from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0020_auto_20151007_1631"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="referee",
            unique_together={("application", "referee_number")},
        ),
    ]
