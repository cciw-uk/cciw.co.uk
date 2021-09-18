from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0017_auto_20151007_1604'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referenceform',
            name='referee',
            field=models.OneToOneField(to='officers.Referee', on_delete=models.CASCADE),
        ),
    ]
