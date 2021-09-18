from django.db import migrations

MAP = {
    'A': 'Green',
    'B': 'Blue',
    'C': 'Orange',
    'D': 'Purple',
    'E': 'Red',
    'F': 'Silver',
}


def forwards(apps, schema_editor):
    CampName = apps.get_model('cciwmain.CampName')
    for from_name, to_name in MAP.items():
        CampName.objects.filter(name=from_name).update(name=to_name, slug=to_name.lower())


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0016_remove_camp_previous_camp'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards)
    ]
