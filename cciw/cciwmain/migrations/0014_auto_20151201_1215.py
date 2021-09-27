from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cciwmain", "0013_remove_camp_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campname",
            name="name",
            field=models.CharField(
                help_text="Name of set of camps. Should start with captial letter", unique=True, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="campname",
            name="slug",
            field=models.SlugField(
                unique=True,
                max_length=255,
                help_text="Name used in URLs and email addresses. Normally just the lowercase version of the name, with spaces replaces by -",
            ),
        ),
    ]
