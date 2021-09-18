from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0009_auto_20151130_1724'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='camp',
            options={'ordering': ['-year', 'start_date']},
        ),
        migrations.AddField(
            model_name='camp',
            name='old_name',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
