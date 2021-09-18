from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0014_auto_20151201_1215'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='camp',
            unique_together={('year', 'camp_name')},
        ),
    ]
