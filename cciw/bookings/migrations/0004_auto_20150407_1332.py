from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0003_auto_20150107_0959"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="bookingaccount",
            unique_together={("name", "email")},
        ),
    ]
