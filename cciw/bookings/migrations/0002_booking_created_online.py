from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='created_online',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
