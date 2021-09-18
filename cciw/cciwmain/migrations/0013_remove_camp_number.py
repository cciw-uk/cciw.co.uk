from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0012_auto_20151201_1154'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camp',
            name='number',
        ),
    ]
