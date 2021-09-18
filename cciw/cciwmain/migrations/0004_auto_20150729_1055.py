from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0003_auto_20150513_0955'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camp',
            name='online_applications',
        ),
        migrations.AlterField(
            model_name='person',
            name='users',
            field=models.ManyToManyField(verbose_name='Associated admin users', blank=True, related_name='people', to=settings.AUTH_USER_MODEL),
        ),
    ]
