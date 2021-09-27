from django.db import migrations


def forwards(apps, schema_editor):
    Camp = apps.get_model("cciwmain.Camp")
    CampName = apps.get_model("cciwmain.CampName")
    if Camp.objects.count() == 0:
        # Empty DB
        return

    # Need to fix up one thing - two camps have same 'previous camp'
    Camp.objects.filter(year=2007, number=5).update(previous_camp=None)

    # Some are incorrect
    Camp.objects.filter(year=2001, number=1).update(previous_camp=Camp.objects.get(year=2000, number=2))
    Camp.objects.filter(year=2001, number=2).update(previous_camp=Camp.objects.get(year=2000, number=7))

    # One old camp has no successors
    null_name = CampName.objects.create(name="Null", slug="null")

    last_year = 2015

    last_year_camps = Camp.objects.filter(year=last_year).order_by("number")
    for i, c in enumerate(last_year_camps):
        name = chr(65 + i)
        cn = CampName.objects.create(name=name, slug=name.lower())
        c.camp_name = cn
        c.save()

    camps_to_process = list(last_year_camps)
    for camp in camps_to_process:
        previous = camp.previous_camp
        if previous is not None:
            previous.camp_name = camp.camp_name
            previous.save()
            camps_to_process.append(previous)

    Camp.objects.filter(camp_name__isnull=True).update(camp_name=null_name)


def backwards(apps, schema_editor):
    Camp = apps.get_model("cciwmain.Camp")
    CampName = apps.get_model("cciwmain.CampName")
    Camp.objects.all().update(camp_name=None)
    CampName.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cciwmain", "0007_camp_name"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
