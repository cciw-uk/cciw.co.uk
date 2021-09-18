from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_auto_20150407_1332'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='bookingaccount',
            unique_together=set(),
        ),
    ]
