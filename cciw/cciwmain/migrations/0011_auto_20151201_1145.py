from django.db import migrations, models


def forwards(apps, schema_editor):
    Camp = apps.get_model('cciwmain.Camp')
    Camp.objects.all().update(old_name=models.F('number'))


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0010_auto_20151201_1145'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards)
    ]
