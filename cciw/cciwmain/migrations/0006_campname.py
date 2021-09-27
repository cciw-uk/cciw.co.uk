from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cciwmain", "0005_camp_last_booking_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampName",
            fields=[
                ("id", models.AutoField(verbose_name="ID", primary_key=True, auto_created=True, serialize=False)),
                (
                    "name",
                    models.CharField(
                        max_length=255, help_text="Name of set of camps. Should start with captial letter"
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Name used in URLs and email addresses. Normally just the lowercase version of the name, with spaces replaces by -",
                        max_length=255,
                    ),
                ),
            ],
        ),
    ]
