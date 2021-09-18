from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0022_auto_20151007_1637'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='referee1_address',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee1_email',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee1_mobile',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee1_name',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee1_tel',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee2_address',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee2_email',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee2_mobile',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee2_name',
        ),
        migrations.RemoveField(
            model_name='application',
            name='referee2_tel',
        ),
    ]
