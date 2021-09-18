from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0011_auto_20151201_1145'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='camp',
            unique_together=set(),
        ),
    ]
