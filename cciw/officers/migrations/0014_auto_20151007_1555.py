from django.db import migrations


def forwards(apps, schema):
    ReferenceAction = apps.get_model("officers", "ReferenceAction")

    for ra in ReferenceAction.objects.select_related("reference__application").all():
        ra.referee = ra.reference.application.referee_set.get(referee_number=ra.reference.referee_number)
        ra.save()


def backwards(apps, schema):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0013_referenceaction_referee"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards, elidable=True),
    ]
