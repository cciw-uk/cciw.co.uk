import datetime

from django.conf import settings
from django.db import migrations, models

import cciw.officers.fields


class Migration(migrations.Migration):

    dependencies = [
        # ("cciwmain", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                (
                    "full_name",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="full name", max_length=100),
                ),
                ("full_maiden_name", models.CharField(blank=True, verbose_name="full maiden name", max_length=100)),
                (
                    "birth_date",
                    cciw.officers.fields.RequiredDateField(
                        null=True, verbose_name="date of birth", default=None, blank=True
                    ),
                ),
                (
                    "birth_place",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="place of birth", max_length=60),
                ),
                (
                    "address_firstline",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="address", max_length=40),
                ),
                (
                    "address_town",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="town/city", max_length=60),
                ),
                (
                    "address_county",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="county", max_length=30),
                ),
                (
                    "address_postcode",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="post code", max_length=10),
                ),
                (
                    "address_country",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="country", max_length=30),
                ),
                (
                    "address_tel",
                    cciw.officers.fields.RequiredCharField(blank=True, verbose_name="telephone", max_length=22),
                ),
                ("address_mobile", models.CharField(blank=True, verbose_name="mobile", max_length=22)),
                (
                    "address_email",
                    cciw.officers.fields.RequiredEmailField(blank=True, verbose_name="e-mail", max_length=75),
                ),
                (
                    "address_since",
                    cciw.officers.fields.RequiredYyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="resident at address since",
                        max_length=7,
                    ),
                ),
                (
                    "address2_from",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="resident at address from",
                        max_length=7,
                    ),
                ),
                (
                    "address2_to",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="resident at address until",
                        max_length=7,
                    ),
                ),
                (
                    "address2_address",
                    cciw.officers.fields.AddressField(
                        blank=True, help_text="Full address, including post code and country", verbose_name="address"
                    ),
                ),
                (
                    "address3_from",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="resident at address from",
                        max_length=7,
                    ),
                ),
                (
                    "address3_to",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="resident at address until",
                        max_length=7,
                    ),
                ),
                (
                    "address3_address",
                    cciw.officers.fields.AddressField(
                        blank=True, help_text="Full address, including post code and country", verbose_name="address"
                    ),
                ),
                (
                    "christian_experience",
                    cciw.officers.fields.RequiredTextField(blank=True, verbose_name="christian experience"),
                ),
                (
                    "youth_experience",
                    cciw.officers.fields.RequiredTextField(blank=True, verbose_name="youth work experience"),
                ),
                (
                    "youth_work_declined",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="Have you ever had an offer to work with children/young people declined?",
                        default=None,
                    ),
                ),
                ("youth_work_declined_details", models.TextField(blank=True, verbose_name="details")),
                (
                    "relevant_illness",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="Do you suffer or have you suffered from any\n            illness which may directly affect your work with children/young people?",
                        default=None,
                    ),
                ),
                ("illness_details", models.TextField(blank=True, verbose_name="illness details")),
                (
                    "employer1_name",
                    models.CharField(blank=True, verbose_name="1. Employer's name and address", max_length=100),
                ),
                (
                    "employer1_from",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="Employed from",
                        max_length=7,
                    ),
                ),
                (
                    "employer1_to",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="Employed until",
                        max_length=7,
                    ),
                ),
                ("employer1_job", models.CharField(blank=True, verbose_name="Job description", max_length=60)),
                ("employer1_leaving", models.CharField(blank=True, verbose_name="Reason for leaving", max_length=150)),
                (
                    "employer2_name",
                    models.CharField(blank=True, verbose_name="2. Employer's name and address", max_length=100),
                ),
                (
                    "employer2_from",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="Employed from",
                        max_length=7,
                    ),
                ),
                (
                    "employer2_to",
                    cciw.officers.fields.YyyyMmField(
                        blank=True,
                        help_text="Enter the date in YYYY/MM format.",
                        verbose_name="Employed until",
                        max_length=7,
                    ),
                ),
                ("employer2_job", models.CharField(blank=True, verbose_name="Job description", max_length=60)),
                ("employer2_leaving", models.CharField(blank=True, verbose_name="Reason for leaving", max_length=150)),
                (
                    "referee1_name",
                    cciw.officers.fields.RequiredCharField(
                        blank=True,
                        help_text="Name only - please do not include job title or other information.",
                        verbose_name="First referee's name",
                        max_length=100,
                    ),
                ),
                (
                    "referee1_address",
                    cciw.officers.fields.RequiredAddressField(
                        blank=True, help_text="Full address, including post code and country", verbose_name="address"
                    ),
                ),
                ("referee1_tel", models.CharField(blank=True, verbose_name="telephone", max_length=22)),
                ("referee1_mobile", models.CharField(blank=True, verbose_name="mobile", max_length=22)),
                ("referee1_email", models.EmailField(blank=True, verbose_name="e-mail", max_length=75)),
                (
                    "referee2_name",
                    cciw.officers.fields.RequiredCharField(
                        blank=True,
                        help_text="Name only - please do not include job title or other information.",
                        verbose_name="Second referee's name",
                        max_length=100,
                    ),
                ),
                (
                    "referee2_address",
                    cciw.officers.fields.RequiredAddressField(
                        blank=True, help_text="Full address, including post code and country", verbose_name="address"
                    ),
                ),
                ("referee2_tel", models.CharField(blank=True, verbose_name="telephone", max_length=22)),
                ("referee2_mobile", models.CharField(blank=True, verbose_name="mobile", max_length=22)),
                ("referee2_email", models.EmailField(blank=True, verbose_name="e-mail", max_length=75)),
                (
                    "crime_declaration",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="Have you ever been charged with or convicted\n            of a criminal offence or are the subject of criminal\n            proceedings?",
                        default=None,
                    ),
                ),
                ("crime_details", models.TextField(blank=True, verbose_name="If yes, give details")),
                (
                    "court_declaration",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="Have you ever been involved in Court\n           proceedings concerning a child for whom you have\n           parental responsibility?",
                        default=None,
                    ),
                ),
                ("court_details", models.TextField(blank=True, verbose_name="If yes, give details")),
                (
                    "concern_declaration",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="Has there ever been any cause for concern\n               regarding your conduct with children/young people?",
                        default=None,
                    ),
                ),
                ("concern_details", models.TextField(blank=True, verbose_name="If yes, give details")),
                (
                    "allegation_declaration",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="To your knowledge have you ever had any\n            allegation made against you concerning children/young people\n            which has been reported to and investigated by Social\n            Services and /or the Police?",
                        default=None,
                    ),
                ),
                (
                    "crb_check_consent",
                    cciw.officers.fields.RequiredExplicitBooleanField(
                        verbose_name="Do you consent to the obtaining of a Criminal\n            Records Bureau check on yourself? ",
                        default=None,
                    ),
                ),
                ("finished", models.BooleanField(verbose_name="is the above information complete?", default=False)),
                ("date_submitted", models.DateField(null=True, verbose_name="date submitted", blank=True)),
                ("officer", models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                "ordering": ("-date_submitted", "officer__first_name", "officer__last_name"),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="CRBApplication",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                ("crb_number", models.CharField(verbose_name="Disclosure number", max_length=20)),
                ("completed", models.DateField(verbose_name="Date of issue")),
                ("officer", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                "verbose_name": "CRB Disclosure",
                "verbose_name_plural": "CRB Disclosures",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="CRBFormLog",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                ("sent", models.DateTimeField(verbose_name="Date sent")),
                ("officer", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                "verbose_name": "CRB form log",
                "verbose_name_plural": "CRB form logs",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                ("date_added", models.DateField(default=datetime.date.today)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("camp", models.ForeignKey(to="cciwmain.Camp", on_delete=models.CASCADE)),
                ("officer", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                "ordering": ("-camp__year", "officer__first_name", "officer__last_name"),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Reference",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                (
                    "referee_number",
                    models.SmallIntegerField(choices=[(1, "1"), (2, "2")], verbose_name="Referee number"),
                ),
                ("requested", models.BooleanField(default=False)),
                ("received", models.BooleanField(default=False)),
                ("comments", models.TextField(blank=True)),
                ("application", models.ForeignKey(to="officers.Application", on_delete=models.CASCADE)),
            ],
            options={
                "verbose_name": "Reference Metadata",
                "verbose_name_plural": "Reference Metadata",
                "ordering": (
                    "application__date_submitted",
                    "application__officer__first_name",
                    "application__officer__last_name",
                    "referee_number",
                ),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="ReferenceForm",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                (
                    "referee_name",
                    models.CharField(
                        help_text="Name only - please do not include job title or other information.",
                        verbose_name="name of referee",
                        max_length=100,
                    ),
                ),
                (
                    "how_long_known",
                    models.CharField(verbose_name="how long/since when have you known the applicant?", max_length=150),
                ),
                ("capacity_known", models.TextField(verbose_name="in what capacity do you know the applicant?")),
                (
                    "known_offences",
                    models.BooleanField(
                        verbose_name="The position for which the applicant is applying requires substantial contact with children and young people. To the best of your knowledge, does the applicant have any convictions/cautions/bindovers, for any criminal offences?",
                        default=False,
                    ),
                ),
                (
                    "known_offences_details",
                    models.TextField(blank=True, verbose_name="If the answer is yes, please identify"),
                ),
                (
                    "capability_children",
                    models.TextField(
                        verbose_name="Please comment on the applicant's capability of working with children and young people (ie. previous experience of similar work, sense of responsibility, sensitivity, ability to work with others, ability to communicate with children and young people, leadership skills)"
                    ),
                ),
                (
                    "character",
                    models.TextField(
                        verbose_name="Please comment on aspects of the applicants character (ie. Christian experience honesty, trustworthiness, reliability, disposition, faithful attendance at worship/prayer meetings.)"
                    ),
                ),
                (
                    "concerns",
                    models.TextField(
                        verbose_name="Have you ever had concerns about either this applicant's ability or suitability to work with children and young people? If you would prefer to discuss your concerns on the telephone and in confidence, please contact: Shirley Evans on 020 8569 0669."
                    ),
                ),
                ("comments", models.TextField(blank=True, verbose_name="Any other comments you wish to make")),
                ("date_created", models.DateField(verbose_name="date created")),
                (
                    "reference_info",
                    models.OneToOneField(
                        related_name="_reference_form", to="officers.Reference", on_delete=models.CASCADE
                    ),
                ),
            ],
            options={
                "verbose_name": "Reference",
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name="reference",
            unique_together={("application", "referee_number")},
        ),
        migrations.AlterUniqueTogether(
            name="invitation",
            unique_together={("officer", "camp")},
        ),
    ]
