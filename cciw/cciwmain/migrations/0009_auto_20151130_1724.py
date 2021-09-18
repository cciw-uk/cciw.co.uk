from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0008_auto_20151130_1654'),
    ]

    operations = [
        migrations.AlterField(
            model_name='camp',
            name='camp_name',
            field=models.ForeignKey(to='cciwmain.CampName', related_name='camps', on_delete=models.CASCADE),
        ),
    ]
