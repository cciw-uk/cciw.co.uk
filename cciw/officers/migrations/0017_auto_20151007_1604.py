from django.db import migrations


def forwards(apps, schema):
    ReferenceForm = apps.get_model("officers", "ReferenceForm")

    for rf in ReferenceForm.objects.select_related("reference_info__application").all():
        rf.referee = rf.reference_info.application.referee_set.get(referee_number=rf.reference_info.referee_number)
        rf.save()


def backwards(apps, schema):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0016_referenceform_referee"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
