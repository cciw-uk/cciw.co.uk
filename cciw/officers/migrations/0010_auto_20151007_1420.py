from django.db import migrations


def forwards(apps, schema):
    Reference = apps.get_model("officers", "Reference")
    ReferenceForm = apps.get_model("officers", "ReferenceForm")

    # To emulate old 'received' field, we need a ReferenceForm to exist.
    for r in list(Reference.objects.filter(received=True, _reference_form__isnull=True)):
        rf = ReferenceForm(
            reference_info=r,
            referee_name=getattr(r.application, f"referee{r.referee_number}_name"),
            inaccurate=True,  # date and other fields which are all empty
            date_created=r.application.date_submitted,
        )  # inaccurate date
        rf.save()
        if not r.actions.filter(action_type="received").exists():
            r.actions.create(
                action_type="received", inaccurate=True, created=r.application.date_submitted
            )  # inaccurate date

    # To emulate old 'requested' field, we now need a ReferenceAction to exist.
    # If there isn't one for references that were requested, we create a fake
    # one.
    for r in list(Reference.objects.filter(requested=True)):
        if not r.actions.filter(action_type="requested").exists():
            r.actions.create(
                action_type="requested", inaccurate=True, created=r.application.date_submitted
            )  # inaccurate date


def backwards(apps, schema):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0009_referenceform_inaccurate"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
