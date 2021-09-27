from decimal import Decimal

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0001_initial"),
        ("cciwmain", "0002_auto_20141231_1034"),
    ]

    operations = [
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.AutoField(primary_key=True, verbose_name="ID", auto_created=True, serialize=False)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("sex", models.CharField(max_length=1, choices=[("m", "Male"), ("f", "Female")])),
                ("date_of_birth", models.DateField()),
                ("address", models.TextField()),
                ("post_code", models.CharField(max_length=10)),
                ("phone_number", models.CharField(max_length=22, blank=True)),
                ("email", models.EmailField(max_length=75, blank=True)),
                ("church", models.CharField(max_length=100, verbose_name="name of church", blank=True)),
                (
                    "south_wales_transport",
                    models.BooleanField(default=False, verbose_name="require transport from South Wales"),
                ),
                ("contact_address", models.TextField()),
                ("contact_post_code", models.CharField(max_length=10)),
                ("contact_phone_number", models.CharField(max_length=22)),
                ("dietary_requirements", models.TextField(blank=True)),
                ("gp_name", models.CharField(max_length=100, verbose_name="GP name")),
                ("gp_address", models.TextField(verbose_name="GP address")),
                ("gp_phone_number", models.CharField(max_length=22, verbose_name="GP phone number")),
                ("medical_card_number", models.CharField(max_length=100)),
                ("last_tetanus_injection", models.DateField(blank=True, null=True)),
                ("allergies", models.TextField(blank=True)),
                ("regular_medication_required", models.TextField(blank=True)),
                ("illnesses", models.TextField(blank=True)),
                ("can_swim_25m", models.BooleanField(default=False, verbose_name="Can the camper swim 25m?")),
                ("learning_difficulties", models.TextField(blank=True)),
                ("serious_illness", models.BooleanField(default=False)),
                ("agreement", models.BooleanField(default=False)),
                (
                    "price_type",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Full price"),
                            (1, "2nd child discount"),
                            (2, "3rd child discount"),
                            (3, "Custom discount"),
                        ]
                    ),
                ),
                ("early_bird_discount", models.BooleanField(help_text="Online bookings only", default=False)),
                ("booked_at", models.DateTimeField(help_text="Online bookings only", blank=True, null=True)),
                ("amount_due", models.DecimalField(decimal_places=2, max_digits=10)),
                ("shelved", models.BooleanField(help_text="Used by user to put on 'shelf'", default=False)),
                (
                    "state",
                    models.IntegerField(
                        help_text="<ul><li>To book, set to 'Booked' <b>and</b> ensure 'Booking expires' is empty</li><li>For people paying online who have been stopped (e.g. due to having a custom discount or serious illness or child too young etc.), set to 'Manually approved' to allow them to book and pay</li><li>If there are queries before it can be booked, set to 'Information complete'</li></ul>",
                        choices=[
                            (0, "Information complete"),
                            (1, "Manually approved"),
                            (2, "Booked"),
                            (3, "Cancelled - deposit kept"),
                            (4, "Cancelled - half refund (pre 2015 only)"),
                            (5, "Cancelled - full refund"),
                        ],
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("booking_expires", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-created"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="BookingAccount",
            fields=[
                ("id", models.AutoField(primary_key=True, verbose_name="ID", auto_created=True, serialize=False)),
                ("email", models.EmailField(max_length=75, blank=True, unique=True, null=True)),
                ("name", models.CharField(max_length=100, blank=True, null=True)),
                ("address", models.TextField(blank=True)),
                ("post_code", models.CharField(max_length=10, blank=True, null=True)),
                ("phone_number", models.CharField(max_length=22, blank=True)),
                (
                    "share_phone_number",
                    models.BooleanField(
                        default=False,
                        verbose_name="Allow this phone number to be passed on to other parents to help organise transport",
                    ),
                ),
                (
                    "email_communication",
                    models.BooleanField(
                        default=True, verbose_name="Receive all communication from CCiW by email where possible"
                    ),
                ),
                ("total_received", models.DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=10)),
                ("first_login", models.DateTimeField(blank=True, null=True)),
                ("last_login", models.DateTimeField(blank=True, null=True)),
                ("last_payment_reminder", models.DateTimeField(blank=True, null=True)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="ManualPayment",
            fields=[
                ("id", models.AutoField(primary_key=True, verbose_name="ID", auto_created=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "payment_type",
                    models.PositiveSmallIntegerField(
                        default=0, choices=[(0, "Cheque"), (1, "Cash"), (2, "e-Cheque"), (3, "Bank transfer")]
                    ),
                ),
                ("account", models.ForeignKey(to="bookings.BookingAccount", on_delete=models.CASCADE)),
            ],
            options={
                "abstract": False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.AutoField(primary_key=True, verbose_name="ID", auto_created=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("origin_id", models.PositiveIntegerField()),
                ("processed", models.DateTimeField(null=True)),
                ("created", models.DateTimeField()),
                ("account", models.ForeignKey(to="bookings.BookingAccount", on_delete=models.CASCADE)),
                ("origin_type", models.ForeignKey(to="contenttypes.ContentType", on_delete=models.CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Price",
            fields=[
                ("id", models.AutoField(primary_key=True, verbose_name="ID", auto_created=True, serialize=False)),
                ("year", models.PositiveSmallIntegerField()),
                (
                    "price_type",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Full price"),
                            (1, "2nd child discount"),
                            (2, "3rd child discount"),
                            (4, "South wales transport surcharge (pre 2015)"),
                            (5, "Deposit"),
                            (6, "Early bird discount"),
                        ]
                    ),
                ),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="RefundPayment",
            fields=[
                ("id", models.AutoField(primary_key=True, verbose_name="ID", auto_created=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "payment_type",
                    models.PositiveSmallIntegerField(
                        default=0, choices=[(0, "Cheque"), (1, "Cash"), (2, "e-Cheque"), (3, "Bank transfer")]
                    ),
                ),
                ("account", models.ForeignKey(to="bookings.BookingAccount", on_delete=models.CASCADE)),
            ],
            options={
                "abstract": False,
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name="price",
            unique_together={("year", "price_type")},
        ),
        migrations.AlterUniqueTogether(
            name="bookingaccount",
            unique_together={("post_code", "name"), ("name", "email")},
        ),
        migrations.AddField(
            model_name="booking",
            name="account",
            field=models.ForeignKey(related_name="bookings", to="bookings.BookingAccount", on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="booking",
            name="camp",
            field=models.ForeignKey(related_name="bookings", to="cciwmain.Camp", on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
