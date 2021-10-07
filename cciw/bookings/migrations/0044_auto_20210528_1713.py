# Generated by Django 3.1.7 on 2021-05-28 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0043_auto_20210528_1702"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="customagreement",
            options={"ordering": ["sort_order"]},
        ),
        migrations.AddField(
            model_name="customagreement",
            name="sort_order",
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="customagreement",
            name="active",
            field=models.BooleanField(default=True),
        ),
    ]