# Generated by Django 4.0.7 on 2022-10-15 13:16

import colorful.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [
        ("cciwmain", "0001_initial"),
        ("cciwmain", "0002_auto_20141231_1034"),
        ("cciwmain", "0003_auto_20150513_0955"),
        ("cciwmain", "0004_auto_20150729_1055"),
        ("cciwmain", "0005_camp_last_booking_date"),
        ("cciwmain", "0006_campname"),
        ("cciwmain", "0007_camp_name"),
        ("cciwmain", "0008_auto_20151130_1654"),
        ("cciwmain", "0009_auto_20151130_1724"),
        ("cciwmain", "0010_auto_20151201_1145"),
        ("cciwmain", "0011_auto_20151201_1145"),
        ("cciwmain", "0012_auto_20151201_1154"),
        ("cciwmain", "0013_remove_camp_number"),
        ("cciwmain", "0014_auto_20151201_1215"),
        ("cciwmain", "0015_auto_20151201_1215"),
        ("cciwmain", "0016_remove_camp_previous_camp"),
        ("cciwmain", "0017_auto_20151201_1238"),
        ("cciwmain", "0018_campname_color"),
        ("cciwmain", "0019_auto_20170410_1828"),
        ("cciwmain", "0020_auto_20170626_2001"),
        ("cciwmain", "0021_camp_special_info_html"),
        ("cciwmain", "0022_auto_20200729_1928"),
        ("cciwmain", "0023_auto_20210412_0837"),
    ]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Site",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("short_name", models.CharField(max_length=25, unique=True, verbose_name="Short name")),
                ("slug_name", models.SlugField(blank=True, max_length=25, unique=True, verbose_name="Machine name")),
                ("long_name", models.CharField(max_length=50, verbose_name="Long name")),
                ("info", models.TextField(verbose_name="Description (HTML)")),
            ],
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=40, verbose_name="Name")),
                ("info", models.TextField(blank=True, verbose_name="Information (Plain text)")),
                (
                    "users",
                    models.ManyToManyField(
                        blank=True,
                        related_name="people",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Associated admin users",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "people",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="CampName",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(
                        help_text="Name of set of camps. Should start with capital letter", max_length=255, unique=True
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Name used in URLs and email addresses. Normally just the lowercase version of the name, with spaces replaces by -",
                        max_length=255,
                        unique=True,
                    ),
                ),
                ("color", colorful.fields.RGBColorField()),
            ],
        ),
        migrations.CreateModel(
            name="Camp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(verbose_name="year")),
                ("minimum_age", models.PositiveSmallIntegerField()),
                ("maximum_age", models.PositiveSmallIntegerField()),
                ("start_date", models.DateField(verbose_name="start date")),
                ("end_date", models.DateField(verbose_name="end date")),
                ("max_campers", models.PositiveSmallIntegerField(default=80, verbose_name="maximum campers")),
                ("max_male_campers", models.PositiveSmallIntegerField(default=60, verbose_name="maximum male campers")),
                (
                    "max_female_campers",
                    models.PositiveSmallIntegerField(default=60, verbose_name="maximum female campers"),
                ),
                (
                    "south_wales_transport_available",
                    models.BooleanField(default=False, verbose_name="South Wales transport available (pre 2015 only)"),
                ),
                (
                    "admins",
                    models.ManyToManyField(
                        blank=True,
                        help_text="These users can manage references/applications for the camp. Not for normal officers.",
                        related_name="camps_as_admin",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="admins",
                    ),
                ),
                (
                    "chaplain",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="camps_as_chaplain",
                        to="cciwmain.person",
                        verbose_name="chaplain",
                    ),
                ),
                (
                    "leaders",
                    models.ManyToManyField(
                        blank=True, related_name="camps_as_leader", to="cciwmain.person", verbose_name="leaders"
                    ),
                ),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="cciwmain.site")),
                (
                    "last_booking_date",
                    models.DateField(blank=True, help_text="Camp start date will be used if left empty.", null=True),
                ),
                (
                    "camp_name",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="camps", to="cciwmain.campname"
                    ),
                ),
                ("old_name", models.CharField(blank=True, max_length=50)),
                (
                    "special_info_html",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="HTML, displayed at the top of the camp details page",
                        verbose_name="Special information",
                    ),
                ),
            ],
            options={
                "ordering": ["-year", "start_date"],
                "unique_together": {("year", "camp_name")},
                "base_manager_name": "objects",
            },
        ),
    ]
